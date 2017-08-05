import requests
# 导入cookielib可以生产cookie并赋给request
try:
    # py2
    import cookielib
except Exception:
    # py3
    import http.cookiejar as cookielib
import re

# session代表的是某一次链接
session = requests.session()
# 这个类实例化出的cookies可以直接调用save方法
session.cookies = cookielib.LWPCookieJar(filename="cookies.txt")

try:
    # 尝试打开cookies
    session.cookies.load(ignore_discard=True)
except Exception:
    print('cookies未能加载')

agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
header = {
    'HOST': 'www.zhihu.com',
    'Referer': 'https://www.zhihu.com',
    'User-Agent': agent
}


def is_login():
    """通过个人页面返回状态码来判断是否为登录状态"""
    inbox_url = 'https://www.zhihu.com/inbox'
    # 如果不加allow_redirects这个参数,服务器给另一个url,session会拿到这个url200的状态码
    response = session.get(inbox_url, headers=header, allow_redirects=False)
    # 查看返回的状态码是否是200,不是200就说明未登录
    if response.status_code != 200:
        return False
    else:
        return True
    pass



def get_xsrf():
    """获取xsrf code"""
    # requests请求的时候不会携带浏览器头,直接
    response = session.get('https://www.zhihu.com', headers=header)
    match_obj = re.search('.*name="_xsrf" value="(.*?)"', response.text)
    # match_obj = re.match('.*(lang).*', response.text)
    print(response.text)
    if match_obj:
        return match_obj.group(1)
    else:
        return ""

def get_index():
    response = session.get('https://www.zhihu.com', headers=header)
    with open('index_page.html', 'wb') as f:
        f.write(response.text.encode('utf-8'))
    print('ok')


def get_captcha():
    import time
    t = str(int(time.time()*1000))
    captcha_url = 'https://www.zhihu.com/captcha.gif?r={0}&type=login&lang=en'.format(t)
    t = session.get(captcha_url, headers=header)
    with open('captcha.jpg', 'wb') as f:
        f.write(t.content)
        f.close()
    from PIL import Image
    try:
        im = Image.open('captcha.jpg')
        im.show()
        im.close()
    except Exception:
        pass
    captcha = input("输入验证码")
    return captcha


def zhihu_login(account, password):
    """知乎登录"""
    if re.match('1\d{10}', account):
        post_url = "https://www.zhihu.com/login/phone_num"
        captcha = get_captcha().split(' ')
        post_data = {
            "_xsrf": get_xsrf(),
            "password": password,
            "captcha_type": 'en',
            "captcha": captcha,
            "phone_num": account
        }
    elif '@' in account:
        post_url = "https://www.zhihu.com/login/email"
        captcha = get_captcha().split(' ')
        post_data = {
            "_xsrf": get_xsrf(),
            "password": password,
            "captcha_type": 'en',
            "captcha": captcha,
            "email": account
        }
    # https://www.zhihu.com/login/email
    response_text = session.post(post_url, data=post_data, headers=header)
    # 保存cookies
    session.cookies.save()

zhihu_login('18659305689', 'zhHAN886158')
# zhihu_login()

# get_index()
# is_login()