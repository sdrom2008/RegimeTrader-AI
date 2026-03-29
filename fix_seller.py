import re

def fix(filename):
    with open(filename, 'r') as f:
        content = f.read()

    pattern = r"""        public static Seller CreateWithPhone\(string phone\)
        \{
            return new Seller
            \{
                Id = Guid\.NewGuid\(\),
                Phone = phone,
                Nickname = \"商户\" \+ DateTime\.Now\.ToString\(\"MMddHHmm\"\),
                FreeQuota = 100,  // 赠送免费额度
                SubscriptionLevel = \"trial\",
                IsActive = true,
                CreatedAt = DateTime\.UtcNow,
                RegisterSource = \"phone\"
            \};
        \}"""

    replacement = """        public static Seller CreateWithPhone(string phone)
        {
            var id = Guid.NewGuid();
            return new Seller
            {
                Id = id,
                OpenId = "phone_" + id.ToString("N"), // 防止数据库 OpenId 唯一索引冲突
                Phone = phone,
                Nickname = "商户" + DateTime.Now.ToString("MMddHHmm"),
                FreeQuota = 100,  // 赠送免费额度
                SubscriptionLevel = "trial",
                IsActive = true,
                CreatedAt = DateTime.UtcNow,
                RegisterSource = "phone"
            };
        }"""
        
    content = re.sub(pattern, replacement, content)

    with open(filename, 'w') as f:
        f.write(content)

fix('Synerixis.Domain/Entities/Seller.cs')
