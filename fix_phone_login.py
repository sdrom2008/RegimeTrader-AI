import re

def fix(filename):
    with open(filename, 'r') as f:
        content = f.read()

    pattern = r"""            // 都找不到，返回未注册
            return Unauthorized\(new \{ message = \"用户不存在\" \}\);"""

    replacement = """            // 都找不到，自动注册为新商户 (Seller)
            var newSeller = Seller.CreateWithPhone(fullPhone);
            _db.Sellers.Add(newSeller);
            await _db.SaveChangesAsync();

            var newToken = _authService.GenerateJwt(newSeller.Id, "Seller", null);
            return Ok(new
            {
                code = 200,
                token = newToken,
                userId = newSeller.Id,
                userType = "Seller",
                nickname = newSeller.Nickname,
                freeQuota = newSeller.FreeQuota,
                subscriptionLevel = newSeller.SubscriptionLevel,
                isNewRegistration = true,
                message = "注册并登录成功"
            });"""
            
    content = re.sub(pattern, replacement, content)

    with open(filename, 'w') as f:
        f.write(content)

fix('Synerixis.Api/Controllers/AuthController.cs')
