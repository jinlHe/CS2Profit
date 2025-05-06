from crawler import save_buff_cookies

def main():
    """保存BUFF登录cookies"""
    print("=== BUFF登录信息保存工具 ===")
    print("此工具将帮助你保存BUFF的登录信息，以便后续自动登录。")
    print("请按照以下步骤操作：")
    print("1. 等待浏览器打开BUFF网站")
    print("2. 在浏览器中完成登录")
    print("3. 登录成功后，按回车键继续")
    print("4. 程序将自动保存登录信息")
    print("==========================")
    
    if save_buff_cookies():
        print("\n登录信息保存成功！")
        print("现在你可以运行 test_crawler.py 来测试自动登录功能。")
    else:
        print("\n登录信息保存失败，请重试。")

if __name__ == "__main__":
    main() 