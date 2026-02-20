import yaml
import os
import requests
import copy
from datetime import datetime


class ConfigManager:
    def __init__(self):
        self.original_file = "original_config.yaml"
        self.custom_file = "user_custom.yaml"
        self.merged_file = "config.yaml"

    def load_config(self):
        """加载合并后的配置"""
        return self.get_merged_config()

    def load_original(self):
        """加载原始订阅配置"""
        if os.path.exists(self.original_file):
            with open(self.original_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def load_custom(self):
        """加载用户自定义配置"""
        if os.path.exists(self.custom_file):
            with open(self.custom_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {"proxy-groups": [], "rules": []}

    def save_custom(self, custom_config):
        """保存用户自定义配置"""
        with open(self.custom_file, "w", encoding="utf-8") as f:
            yaml.dump(custom_config, f, allow_unicode=True, default_flow_style=False)

    def get_merged_config(self):
        """合并原始配置和自定义配置"""
        original = self.load_original()
        custom = self.load_custom()

        # 深拷贝原始配置
        merged = copy.deepcopy(original)

        # 合并 proxy-groups
        if "proxy-groups" in merged and "proxy-groups" in custom:
            merged_groups = {g["name"]: g for g in merged["proxy-groups"]}
            custom_groups = {g["name"]: g for g in custom["proxy-groups"]}

            # 更新已存在的组
            for name, custom_group in custom_groups.items():
                if name in merged_groups:
                    # 合并配置，自定义优先
                    merged_groups[name].update(custom_group)
                else:
                    # 新增组
                    merged_groups[name] = custom_group

            merged["proxy-groups"] = list(merged_groups.values())

        # 合并 rules
        if "rules" in custom:
            # 在原始 rules 基础上追加自定义 rules
            if "rules" not in merged:
                merged["rules"] = []
            # 避免重复，根据规则内容判断
            existing_rules = set(str(r) for r in merged["rules"])
            for rule in custom["rules"]:
                if str(rule) not in existing_rules:
                    merged["rules"].append(rule)

        return merged

    def add_proxy_group(self, group_data):
        """添加代理组"""
        custom = self.load_custom()
        if "proxy-groups" not in custom:
            custom["proxy-groups"] = []

        # 检查是否已存在
        for i, g in enumerate(custom["proxy-groups"]):
            if g.get("name") == group_data["name"]:
                return {"success": False, "message": "代理组名称已存在"}

        custom["proxy-groups"].append(group_data)
        self.save_custom(custom)
        return {"success": True, "message": "添加成功"}

    def update_proxy_group(self, group_data):
        """更新代理组"""
        custom = self.load_custom()
        original = self.load_original()

        name = group_data["name"]
        old_name = group_data.get("old_name", name)

        # 先在自定义配置中查找
        found = False
        for i, g in enumerate(custom.get("proxy-groups", [])):
            if g.get("name") == old_name:
                custom["proxy-groups"][i] = group_data
                found = True
                break

        # 如果自定义中没找到，在原始配置中查找并添加到自定义
        if not found:
            for g in original.get("proxy-groups", []):
                if g.get("name") == old_name:
                    group_data["old_name"] = old_name
                    custom["proxy-groups"].append(group_data)
                    found = True
                    break

        if found:
            self.save_custom(custom)
            return {"success": True, "message": "更新成功"}
        return {"success": False, "message": "未找到该代理组"}

    def delete_proxy_group(self, name):
        """删除代理组（从自定义配置中移除）"""
        custom = self.load_custom()
        custom["proxy-groups"] = [
            g for g in custom.get("proxy-groups", []) if g.get("name") != name
        ]
        self.save_custom(custom)
        return {"success": True, "message": "删除成功"}

    def add_rule(self, rule_data):
        """添加规则"""
        custom = self.load_custom()
        if "rules" not in custom:
            custom["rules"] = []

        # 构建规则字符串
        rule_parts = [rule_data["type"], rule_data["value"], rule_data["proxy"]]
        if rule_data.get("no_resolve"):
            rule_parts.append("no-resolve")
        rule_str = ",".join(rule_parts)

        # 检查是否已存在
        for rule in custom["rules"]:
            if isinstance(rule, str) and rule == rule_str:
                return {"success": False, "message": "规则已存在"}

        custom["rules"].append(rule_str)
        self.save_custom(custom)
        return {"success": True, "message": "添加成功"}

    def update_rule(self, rule_data):
        """更新规则"""
        custom = self.load_custom()
        index = rule_data.get("index")

        if index is not None and 0 <= index < len(custom.get("rules", [])):
            rule_parts = [rule_data["type"], rule_data["value"], rule_data["proxy"]]
            if rule_data.get("no_resolve"):
                rule_parts.append("no-resolve")
            custom["rules"][index] = ",".join(rule_parts)
            self.save_custom(custom)
            return {"success": True, "message": "更新成功"}

        return {"success": False, "message": "无效的规则索引"}

    def delete_rule(self, index):
        """删除规则"""
        custom = self.load_custom()
        if index is not None and 0 <= index < len(custom.get("rules", [])):
            custom["rules"].pop(index)
            self.save_custom(custom)
            return {"success": True, "message": "删除成功"}
        return {"success": False, "message": "无效的规则索引"}

    def save_config(self):
        """保存合并后的配置"""
        merged = self.get_merged_config()
        with open(self.merged_file, "w", encoding="utf-8") as f:
            yaml.dump(merged, f, allow_unicode=True, default_flow_style=False)
        return {"success": True, "message": "配置已保存"}

    def refresh_subscription(self, subscription_url):
        """刷新订阅并合并自定义配置"""
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

            # 保存合并后的配置
            self.save_config()

            return {"success": True, "message": "订阅更新成功，自定义配置已合并"}
        except Exception as e:
            return {"success": False, "message": f"更新失败：{str(e)}"}

    def move_rule(self, index, direction):
        """移动规则位置"""
        custom = self.load_custom()
        rules = custom.get('rules', [])
        
        if direction == 'up' and index > 0:
            rules[index], rules[index - 1] = rules[index - 1], rules[index]
        elif direction == 'down' and index < len(rules) - 1:
            rules[index], rules[index + 1] = rules[index + 1], rules[index]
        else:
            return {'success': False, 'message': '无法移动'}
        
        custom['rules'] = rules
        self.save_custom(custom)
        return {'success': True, 'message': '移动成功'}