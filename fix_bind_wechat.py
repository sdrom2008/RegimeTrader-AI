import re

def fix(filename):
    with open(filename, 'r') as f:
        content = f.read()

    pattern = r"""        public void BindWechat\(string openId\)
        \{
            if \(!string\.IsNullOrEmpty\(OpenId\)\)
                throw new InvalidOperationException\(\"微信已绑定，不可重复设置\"\);

            OpenId = openId;
        \}"""

    replacement = """        public void BindWechat(string openId)
        {
            if (!string.IsNullOrEmpty(OpenId) && !OpenId.StartsWith("phone_"))
                throw new InvalidOperationException("微信已绑定，不可重复设置");

            OpenId = openId;
        }"""
        
    content = re.sub(pattern, replacement, content)

    with open(filename, 'w') as f:
        f.write(content)

fix('Synerixis.Domain/Entities/Seller.cs')
