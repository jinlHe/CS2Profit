from crawler import save_c5_cookies

def main():
    """保存C5登录cookies,注意，必须进入到user/user页面才能回车，这个获取的才可以"""
    print("=== C5登录信息保存工具 ===")
    print("此工具将帮助你保存C5的登录信息，以便后续自动登录。")
    
    # 使用您提供的cookie字符串
    cookie_str=""
    if save_c5_cookies(cookie_str):
        print("\n登录信息保存成功！")
        print("现在你可以刷新页面来更新C5余额。")
    else:
        print("\n登录信息保存失败，请重试。")

if __name__ == "__main__":
    main() 