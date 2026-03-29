import re

def fix(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # Fix SendCode
    send_code_pattern = r"""            if \(_env\.IsDevelopment\(\)\)
            \{
                _cache\.Set\(\$\"sms:\{fullPhone\}\", code, TimeSpan\.FromMinutes\(5\)\);
                return Ok\(new \{ message = \"验证码已发送（开发环境固定为 123456）\" \}\);
            \}"""
            
    send_code_replacement = """            // 如果是开发环境，或未配置阿里云短信（即AccessKeyId为空），均使用固定验证码 123456 进行测试
            if (_env.IsDevelopment() || string.IsNullOrEmpty(_config["AliyunSms:AccessKeyId"]))
            {
                _cache.Set($"sms:{fullPhone}", code, TimeSpan.FromMinutes(5));
                return Ok(new { message = "测试模式已开启（验证码: 123456）" });
            }"""
            
    content = re.sub(send_code_pattern, send_code_replacement, content)

    # Fix PhoneLogin
    phone_login_pattern = r"""            // 开发环境：跳过验证码检查，直接登录
            if \(_env\.IsDevelopment\(\)\)
            \{
                // 开发环境任意验证码通过（简化测试）
            \}
            else
            \{
                if \(!_cache\.TryGetValue\(\$\"sms:\{fullPhone\}\", out string cachedCode\) \|\| cachedCode != dto\.Code\)
                    return BadRequest\(\"验证码错误或已过期\"\);
            \}"""
            
    phone_login_replacement = """            // 开发环境或未配置短信网关时，允许测试验证码通过
            if (_env.IsDevelopment() || string.IsNullOrEmpty(_config["AliyunSms:AccessKeyId"]))
            {
                if (dto.Code != "123456" && (!_cache.TryGetValue($"sms:{fullPhone}", out string cachedCode) || cachedCode != dto.Code))
                    return BadRequest("验证码错误或已过期");
            }
            else
            {
                if (!_cache.TryGetValue($"sms:{fullPhone}", out string cachedCode) || cachedCode != dto.Code)
                    return BadRequest("验证码错误或已过期");
            }"""
            
    content = re.sub(phone_login_pattern, phone_login_replacement, content)
    
    # Fix BindPhone
    bind_phone_pattern = r"""            // TODO: 校验验证码"""
    bind_phone_replacement = """            // 校验验证码
            var fullPhoneCode = $"+{dto.CountryCode}{dto.Phone}".Replace(" ", "");
            if (_env.IsDevelopment() || string.IsNullOrEmpty(_config["AliyunSms:AccessKeyId"]))
            {
                if (dto.Code != "123456" && (!_cache.TryGetValue($"sms:{fullPhoneCode}", out string cachedCode) || cachedCode != dto.Code))
                    return BadRequest("验证码错误或已过期");
            }
            else
            {
                if (!_cache.TryGetValue($"sms:{fullPhoneCode}", out string cachedCode) || cachedCode != dto.Code)
                    return BadRequest("验证码错误或已过期");
            }"""
    
    content = re.sub(bind_phone_pattern, bind_phone_replacement, content)

    with open(filename, 'w') as f:
        f.write(content)

fix('Synerixis.Api/Controllers/AuthController.cs')
