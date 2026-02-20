import yaml
import os
import requests
import copy
import json
from datetime import datetime


class ConfigManager:
    def __init__(self):
        self.original_file = "original_config.yaml"
        self.modified_file = "modified_config.yaml"
        self.modifications_dir = "modifications"  # 存放修改文件的目录
        
        # 创建修改文件目录
        if not os.path.exists(self.modifications_dir):
            os.makedirs(self.modifications_dir)

    def load_config(self):
        """加载合并后的配置"""
        return self.get_merged_config()

    def load_original(self):
        """加载原始订阅配置"""
        if os.path.exists(self.original_file):
            with open(self.original_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def load_modified(self):
        """加载修改后的配置"""
        if os.path.exists(self.modified_file):
            with open(self.modified_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        # 如果没有修改过，返回原始配置的副本
        return copy.deepcopy(self.load_original())

    def save_modified(self, config):
        """保存修改后的配置"""
        with open(self.modified_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def get_merged_config(self):
        """加载修改后的配置（基于 modified_config.yaml）"""
        return self.load_modified()

    def add_proxy_group(self, group_data):
        """添加代理组"""
        modified = self.load_modified()
        if "proxy-groups" not in modified:
            modified["proxy-groups"] = []

        # 检查是否已存在
        for i, g in enumerate(modified["proxy-groups"]):
            if g.get("name") == group_data["name"]:
                return {"success": False, "message": "代理组名称已存在"}

        modified["proxy-groups"].append(group_data)
        self.save_modified(modified)
        return {"success": True, "message": "添加成功"}

    def update_proxy_group(self, group_data):
        """更新代理组"""
        modified = self.load_modified()
        original = self.load_original()

        name = group_data["name"]
        old_name = group_data.get("old_name", name)

        # 先在修改的配置中查找
        found = False
        for i, g in enumerate(modified.get("proxy-groups", [])):
            if g.get("name") == old_name:
                modified["proxy-groups"][i] = group_data
                found = True
                break

        # 如果修改中没找到，在原始配置中查找并添加到修改
        if not found:
            for g in original.get("proxy-groups", []):
                if g.get("name") == old_name:
                    group_data["old_name"] = old_name
                    modified["proxy-groups"].append(group_data)
                    found = True
                    break

        if found:
            self.save_modified(modified)
            return {"success": True, "message": "更新成功"}
        return {"success": False, "message": "未找到该代理组"}

    def delete_proxy_group(self, name):
        """删除代理组"""
        modified = self.load_modified()
        modified["proxy-groups"] = [
            g for g in modified.get("proxy-groups", []) if g.get("name") != name
        ]
        self.save_modified(modified)
        return {"success": True, "message": "删除成功"}

    def add_rule(self, rule_data):
        """添加规则"""
        modified = self.load_modified()
        if "rules" not in modified:
            modified["rules"] = []

        # 构建规则字符串
        rule_parts = [rule_data["type"], rule_data["value"], rule_data["proxy"]]
        if rule_data.get("no_resolve"):
            rule_parts.append("no-resolve")
        rule_str = ",".join(rule_parts)

        # 检查是否已存在
        for rule in modified["rules"]:
            if isinstance(rule, str) and rule == rule_str:
                return {"success": False, "message": "规则已存在"}

        modified["rules"].append(rule_str)
        self.save_modified(modified)
        return {"success": True, "message": "添加成功"}

    def update_rule(self, rule_data):
        """更新规则"""
        modified = self.load_modified()
        index = rule_data.get("index")

        if index is not None and 0 <= index < len(modified.get("rules", [])):
            rule_parts = [rule_data["type"], rule_data["value"], rule_data["proxy"]]
            if rule_data.get("no_resolve"):
                rule_parts.append("no-resolve")
            modified["rules"][index] = ",".join(rule_parts)
            self.save_modified(modified)
            return {"success": True, "message": "更新成功"}

        return {"success": False, "message": "无效的规则索引"}

    def delete_rule(self, index):
        """删除规则"""
        modified = self.load_modified()
        if index is not None and 0 <= index < len(modified.get("rules", [])):
            modified["rules"].pop(index)
            self.save_modified(modified)
            return {"success": True, "message": "删除成功"}
        return {"success": False, "message": "无效的规则索引"}

    def move_rule(self, index, direction):
        """移动规则位置"""
        modified = self.load_modified()
        rules = modified.get('rules', [])
        
        if direction == 'up' and index > 0:
            rules[index], rules[index - 1] = rules[index - 1], rules[index]
        elif direction == 'down' and index < len(rules) - 1:
            rules[index], rules[index + 1] = rules[index + 1], rules[index]
        else:
            return {'success': False, 'message': '无法移动'}
        
        modified['rules'] = rules
        self.save_modified(modified)
        return {'success': True, 'message': '移动成功'}

    def refresh_subscription(self, subscription_url):
        """刷新订阅（下载新配置到 original_config.yaml）"""
        if not subscription_url:
            return {"success": False, "message": "请提供订阅 URL"}

        try:
            # 下载新订阅
            response = requests.get(subscription_url, timeout=30)
            response.raise_for_status()

            # 保存为原始配置
            new_config = yaml.safe_load(response.text)
            with open(self.original_file, "w", encoding="utf-8") as f:
                yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False)

            return {"success": True, "message": "订阅更新成功"}
        except Exception as e:
            return {"success": False, "message": f"更新失败：{str(e)}"}

    # ==================== 修改文件管理 ====================
    
    def save_modification(self, mod_name, mod_description):
        """保存修改文件（对比 original_config.yaml 和 modified_config.yaml）
        
        记录增量修改：
        - 新增的代理组
        - 修改的代理组
        - 删除的代理组
        - 新增的规则
        - 修改的规则
        - 删除的规则
        
        Args:
            mod_name: 修改名称
            mod_description: 修改描述
        """
        try:
            # 加载原始配置和修改后的配置
            original = self.load_original()
            modified = self.load_modified()
            
            # 生成修改文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{mod_name}_{timestamp}.json"
            filepath = os.path.join(self.modifications_dir, filename)
            
            # 分析代理组的变化
            original_groups = {g["name"]: g for g in original.get("proxy-groups", [])}
            modified_groups = {g["name"]: g for g in modified.get("proxy-groups", [])}
            
            added_groups = []
            modified_group_list = []
            deleted_group_names = []
            
            # 找出新增和修改的代理组
            for name, group in modified_groups.items():
                if name not in original_groups:
                    # 新增的代理组
                    added_groups.append(group)
                elif original_groups[name] != group:
                    # 修改的代理组 - 详细记录节点变化
                    old_group = original_groups[name]
                    new_group = group
                    
                    # 获取代理节点（proxies 字段）
                    old_proxies = set(old_group.get("proxies", []))
                    new_proxies = set(new_group.get("proxies", []))
                    
                    # 计算节点的添加、删除
                    added_proxies = list(new_proxies - old_proxies)
                    deleted_proxies = list(old_proxies - new_proxies)
                    
                    # 检查其他字段的改变
                    fields_changed = {}
                    for key in old_group:
                        if key != "proxies" and old_group.get(key) != new_group.get(key):
                            fields_changed[key] = {
                                "old": old_group.get(key),
                                "new": new_group.get(key)
                            }
                    
                    # 如果有任何改变，才记录为修改
                    if added_proxies or deleted_proxies or fields_changed:
                        modified_group_list.append({
                            "name": name,
                            "added_proxies": added_proxies,
                            "deleted_proxies": deleted_proxies,
                            "fields_changed": fields_changed,
                            "old": old_group,
                            "new": new_group
                        })
            
            # 找出删除的代理组（原始中有，修改中没有）
            for name in original_groups:
                if name not in modified_groups:
                    deleted_group_names.append(name)
            
            # 分析规则的变化
            original_rules = original.get("rules", [])
            modified_rules = modified.get("rules", [])
            
            added_rules = []
            modified_rule_list = []
            deleted_rules = []
            
            # 创建规则映射（用于对比）
            original_rules_set = set(str(r) for r in original_rules)
            modified_rules_set = set(str(r) for r in modified_rules)
            
            # 找出新增的规则
            for rule in modified_rules:
                rule_str = str(rule)
                if rule_str not in original_rules_set:
                    added_rules.append(rule)
            
            # 找出删除的规则
            for rule in original_rules:
                rule_str = str(rule)
                if rule_str not in modified_rules_set:
                    deleted_rules.append(rule)
            
            # 检测规则的顺序是否改变（视为修改）
            if original_rules != modified_rules and added_rules == [] and deleted_rules == []:
                # 只有顺序改变，记录为修改
                modified_rule_list.append({
                    "type": "reorder",
                    "old_rules": original_rules,
                    "new_rules": modified_rules
                })
            
            # 准备修改数据
            modification = {
                "name": mod_name,
                "description": mod_description,
                "created_at": datetime.now().isoformat(),
                "proxy_groups": {
                    "added": added_groups,
                    "modified": modified_group_list,
                    "deleted": deleted_group_names
                },
                "rules": {
                    "added": added_rules,
                    "modified": modified_rule_list,
                    "deleted": deleted_rules
                }
            }
            
            # 保存修改文件
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(modification, f, ensure_ascii=False, indent=2)
            
            return {"success": True, "message": "修改已保存", "filename": filename}
        except Exception as e:
            return {"success": False, "message": f"保存失败：{str(e)}"}

    def get_modifications_list(self):
        """获取所有修改文件列表"""
        try:
            modifications = []
            if os.path.exists(self.modifications_dir):
                for filename in os.listdir(self.modifications_dir):
                    if filename.endswith(".json"):
                        filepath = os.path.join(self.modifications_dir, filename)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                mod_data = json.load(f)
                            
                            # 统计变化
                            pg = mod_data.get("proxy_groups", {})
                            rules = mod_data.get("rules", {})
                            
                            changes_summary = []
                            if pg.get("added"):
                                changes_summary.append(f"新增代理组{len(pg['added'])}")
                            if pg.get("modified"):
                                changes_summary.append(f"修改代理组{len(pg['modified'])}")
                            if pg.get("deleted"):
                                changes_summary.append(f"删除代理组{len(pg['deleted'])}")
                            if rules.get("added"):
                                changes_summary.append(f"新增规则{len(rules['added'])}")
                            if rules.get("modified"):
                                changes_summary.append(f"修改规则{len(rules['modified'])}")
                            if rules.get("deleted"):
                                changes_summary.append(f"删除规则{len(rules['deleted'])}")
                            
                            modifications.append({
                                "filename": filename,
                                "name": mod_data.get("name", "未命名"),
                                "description": mod_data.get("description", ""),
                                "created_at": mod_data.get("created_at", ""),
                                "changes_summary": ", ".join(changes_summary)
                            })
                        except:
                            pass
            
            # 按创建时间倒序排列
            modifications.sort(key=lambda x: x["created_at"], reverse=True)
            return {"success": True, "modifications": modifications}
        except Exception as e:
            return {"success": False, "message": f"获取列表失败：{str(e)}"}
    
    def load_modification(self, filename):
        """加载修改文件"""
        try:
            filepath = os.path.join(self.modifications_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                mod_data = json.load(f)
            return {
                "success": True,
                "modification": mod_data
            }
        except Exception as e:
            return {"success": False, "message": f"加载失败：{str(e)}"}

    def apply_modification(self, filename):
        """应用修改文件（合并到当前配置）
        
        根据修改文件中记录的增量变化，将其应用到当前配置：
        1. 添加新的代理组/规则
        2. 更新修改的代理组/规则
        3. 删除指定的代理组/规则
        """
        try:
            # 加载修改文件
            load_result = self.load_modification(filename)
            if not load_result["success"]:
                return load_result
            
            mod_data = load_result["modification"]
            
            # 加载当前的修改配置
            modified = self.load_modified()
            
            if "proxy-groups" not in modified:
                modified["proxy-groups"] = []
            if "rules" not in modified:
                modified["rules"] = []
            
            # ========== 处理代理组变化 ==========
            pg_changes = mod_data.get("proxy_groups", {})
            
            # 1. 添加新的代理组
            if pg_changes.get("added"):
                modified_group_names = {g["name"] for g in modified["proxy-groups"]}
                for added_group in pg_changes["added"]:
                    if added_group["name"] not in modified_group_names:
                        modified["proxy-groups"].append(added_group)
            
            # 2. 更新修改的代理组（智能应用节点级别的变化）
            if pg_changes.get("modified"):
                modified_groups = {g["name"]: i for i, g in enumerate(modified["proxy-groups"])}
                for mod_group in pg_changes["modified"]:
                    group_name = mod_group["name"]
                    
                    if group_name in modified_groups:
                        group_idx = modified_groups[group_name]
                        current_group = modified["proxy-groups"][group_idx]
                        
                        # 智能应用节点级别的变化
                        if mod_group.get("added_proxies") or mod_group.get("deleted_proxies"):
                            # 如果有节点级别的变化，进行精确的节点操作
                            current_proxies = set(current_group.get("proxies", []))
                            
                            # 添加新节点
                            if mod_group.get("added_proxies"):
                                for proxy in mod_group["added_proxies"]:
                                    current_proxies.add(proxy)
                            
                            # 删除指定的节点
                            if mod_group.get("deleted_proxies"):
                                current_proxies.difference_update(mod_group["deleted_proxies"])
                            
                            current_group["proxies"] = list(current_proxies)
                        
                        # 应用其他字段的改变
                        if mod_group.get("fields_changed"):
                            for field, change in mod_group["fields_changed"].items():
                                current_group[field] = change["new"]
                        
                        modified["proxy-groups"][group_idx] = current_group
                    else:
                        # 如果代理组不存在，则添加新的
                        modified["proxy-groups"].append(mod_group["new"])
            
            # 3. 删除指定的代理组
            if pg_changes.get("deleted"):
                deleted_names = set(pg_changes["deleted"])
                modified["proxy-groups"] = [
                    g for g in modified["proxy-groups"] 
                    if g["name"] not in deleted_names
                ]
            
            # ========== 处理规则变化 ==========
            rules_changes = mod_data.get("rules", {})
            
            # 1. 添加新的规则
            if rules_changes.get("added"):
                existing_rules = set(str(r) for r in modified["rules"])
                for added_rule in rules_changes["added"]:
                    if str(added_rule) not in existing_rules:
                        modified["rules"].append(added_rule)
            
            # 2. 处理修改的规则（主要是顺序改变）
            if rules_changes.get("modified"):
                for mod_rule in rules_changes["modified"]:
                    if mod_rule.get("type") == "reorder":
                        # 恢复为修改文件中的规则顺序
                        modified["rules"] = mod_rule["new_rules"]
            
            # 3. 删除指定的规则
            if rules_changes.get("deleted"):
                deleted_rules_set = set(str(r) for r in rules_changes["deleted"])
                modified["rules"] = [
                    r for r in modified["rules"]
                    if str(r) not in deleted_rules_set
                ]
            
            # 保存修改后的配置
            self.save_modified(modified)
            
            # 统计应用的变化
            changes_count = []
            if pg_changes.get("added"):
                changes_count.append(f"新增{len(pg_changes['added'])}个代理组")
            if pg_changes.get("modified"):
                changes_count.append(f"修改{len(pg_changes['modified'])}个代理组")
            if pg_changes.get("deleted"):
                changes_count.append(f"删除{len(pg_changes['deleted'])}个代理组")
            if rules_changes.get("added"):
                changes_count.append(f"新增{len(rules_changes['added'])}条规则")
            if rules_changes.get("modified"):
                changes_count.append(f"修改规则顺序")
            if rules_changes.get("deleted"):
                changes_count.append(f"删除{len(rules_changes['deleted'])}条规则")
            
            change_detail = "，".join(changes_count) if changes_count else "无变化"
            
            return {
                "success": True,
                "message": f"已应用修改：{mod_data.get('name', '未命名')}（{change_detail}）"
            }
        except Exception as e:
            return {"success": False, "message": f"应用失败：{str(e)}"}

    def delete_modification(self, filename):
        """删除修改文件"""
        try:
            filepath = os.path.join(self.modifications_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return {"success": True, "message": "修改已删除"}
            return {"success": False, "message": "修改文件不存在"}
        except Exception as e:
            return {"success": False, "message": f"删除失败：{str(e)}"}

    def get_current_config(self):
        """获取当前配置（modified_config.yaml）"""
        return self.load_modified()
