"""
风险控制器 - 决定操作动作
"""

from datetime import datetime
from config_news_sentiment import WARNING_THRESHOLD, CRITICAL_THRESHOLD, SEND_WHATSAPP_ALERT, WHATSAPP_TARGET

class RiskController:
    def __init__(self):
        self.current_risk_level = 0  # 0: normal, 1: warning, 2: critical
        self.last_update = None
        self.reason = ""
    
    def assess_risk(self, risk_score, has_critical, details):
        """
        根据风险评分决定操作
        Returns: {
            'level': 0/1/2,
            'action': 'NORMAL'|'REDUCE'|'HALT_NEW_ENTRIES'|'CLOSE_ALL',
            'message': 人类可读描述,
            'details': details
        }
        """
        level = 0
        action = "NORMAL"
        reason = ""
        
        if risk_score >= CRITICAL_THRESHOLD or has_critical:
            level = 2
            action = "HALT_NEW_ENTRIES"  # 暂缓新开仓，可继续观察或平仓
            reason = f"Critical event detected (score={risk_score:.1%})"
        elif risk_score >= WARNING_THRESHOLD:
            level = 1
            action = "REDUCE"  # 降低仓位规模（例如单笔风险降至4%）
            reason = f"High negative sentiment (score={risk_score:.1%})"
        else:
            level = 0
            action = "NORMAL"
            reason = ""
        
        self.current_risk_level = level
        self.last_update = datetime.utcnow()
        self.reason = reason
        
        return {
            'level': level,
            'action': action,
            'risk_score': risk_score,
            'has_critical': has_critical,
            'message': reason,
            'details': details,
            'timestamp': self.last_update.isoformat() + 'Z'
        }
    
    def should_allow_new_entry(self, risk_assessment):
        """是否允许新开仓"""
        level = risk_assessment['level']
        if level == 2:
            return False, risk_assessment['reason']
        return True, "OK"
    
    def adjust_position_size(self, base_risk_pct, risk_assessment):
        """根据风险级别调整仓位大小"""
        level = risk_assessment['level']
        if level == 2:
            return 0.0  # 禁止开仓
        elif level == 1:
            return base_risk_pct * 0.5  # 减半
        return base_risk_pct
    
    def format_alert(self, risk_assessment):
        """生成 WhatsApp 警报文本"""
        level_names = {0: "正常", 1: "警告", 2: "严重"}
        msg = f"🛡️ 宏观风险监控 - {level_names[risk_assessment['level']]}\n"
        msg += f"🕒 {risk_assessment['timestamp']}\n"
        reason = risk_assessment.get('reason') or risk_assessment.get('message')
        if reason:
            msg += f"⚠️ {reason}\n"
        msg += f"📊 风险分数: {risk_assessment['risk_score']:.1%}\n"
        if risk_assessment.get('details'):
            msg += "\n🔍 高影响新闻:\n"
            for d in risk_assessment['details'][:3]:
                if d.get('score', 0) > 0.2 or d.get('critical'):
                    crit = "🚨" if d.get('critical') else ""
                    msg += f"{crit} {d['title'][:50]}... ({d['source']})\n"
        return msg

if __name__ == '__main__':
    import json
    # 模拟测试
    controller = RiskController()
    fake_risk = 0.45
    has_crit = False
    details = [{'title': 'Test news', 'source': 'test', 'score': 0.45, 'critical': False, 'link': ''}]
    
    assessment = controller.assess_risk(fake_risk, has_crit, details)
    print(json.dumps(assessment, indent=2, ensure_ascii=False))
    
    print("\nAlert message:")
    print(controller.format_alert(assessment))
