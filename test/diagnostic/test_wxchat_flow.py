"""
测试 baidu-download.exe --wxchat 的完整流程
诊断为什么流程串不起来
"""

import sys
import os
from datetime import datetime, timedelta

def test_config():
    """测试配置加载"""
    print("=" * 60)
    print("[1/5] 测试配置加载")
    print("=" * 60)

    try:
        from src.config.settings import Settings

        settings = Settings()

        print(f"[OK] Config loaded successfully")
        print(f"   wewe_db_host: {settings.wxchat_wewe_db_host}")
        print(f"   wewe_db_name: {settings.wxchat_wewe_db_name}")
        print(f"   base_url: {settings.wxchat_base_url}")
        print(f"   sftp_remote_path: {settings.wxchat_sftp_remote_path}")

        return settings
    except Exception as e:
        print(f"[FAIL] Config load failed: {e}")
        return None

def test_database_connection(settings):
    """测试数据库连接"""
    print("\n" + "=" * 60)
    print("[2/5] 测试数据库连接")
    print("=" * 60)

    try:
        from src.wxchat.processor import DatabaseConnection

        print(f"连接到 wewe_rss 数据库...")
        with DatabaseConnection(settings, use_wewe_db=True) as conn:
            with conn.cursor() as cursor:
                # 测试查询文章数量
                cursor.execute("SELECT COUNT(*) as count FROM articles")
                result = cursor.fetchone()
                print(f"[OK] Database connected successfully")
                print(f"   articles表总文章数: {result['count']}")

                # 测试查询最近文章
                cursor.execute("""
                    SELECT id, mp_id, title, publish_time
                    FROM articles
                    ORDER BY publish_time DESC
                    LIMIT 5
                """)
                articles = cursor.fetchall()
                print(f"   最近5篇文章:")
                for i, article in enumerate(articles, 1):
                    try:
                        title_safe = article['title'][:50].encode('ascii', 'ignore').decode('ascii')
                    except:
                        title_safe = "Chinese title (encoding issue)"
                    print(f"     {i}. {title_safe}... (ID: {article['id']})")

                return articles
    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        return None

def test_url_generation(settings, articles):
    """测试URL生成"""
    print("\n" + "=" * 60)
    print("[3/5] 测试URL生成")
    print("=" * 60)

    if not articles:
        print("[SKIP] No article data, skip URL test")
        return None

    try:
        from src.wxchat.processor import PDFGenerator

        pdf_gen = PDFGenerator(settings)

        # 测试第一篇文章的URL生成
        article = articles[0]
        article_id = article['id']
        generated_url = f"{pdf_gen.base_url}{article_id}"

        print(f"[OK] URL generation successful")
        print(f"   Article ID: {article_id}")
        print(f"   Generated URL: {generated_url}")
        try:
            title_safe = article['title'][:50].encode('ascii', 'ignore').decode('ascii')
        except:
            title_safe = "Chinese title (encoding issue)"
        print(f"   Article title: {title_safe}...")

        return generated_url
    except Exception as e:
        print(f"[FAIL] URL generation failed: {e}")
        return None

def test_pdf_generation(settings, url):
    """测试PDF生成"""
    print("\n" + "=" * 60)
    print("[4/5] 测试PDF生成")
    print("=" * 60)

    if not url:
        print("[SKIP] No valid URL, skip PDF test")
        return False

    try:
        from src.wxchat.processor import PDFGenerator

        pdf_gen = PDFGenerator(settings)
        test_pdf_path = "test_flow_article.pdf"

        # 提取article_id
        article_id = url.split('/s/')[-1].split('?')[0]

        print(f"测试生成PDF: {url}")
        success = pdf_gen.generate_pdf(article_id, test_pdf_path)

        if success:
            file_size = os.path.getsize(test_pdf_path)
            print(f"[OK] PDF generated successfully")
            print(f"   文件大小: {file_size:,} bytes ({file_size/1024:.2f} KB)")
            print(f"   文件路径: {os.path.abspath(test_pdf_path)}")

            # 清理测试文件
            try:
                os.unlink(test_pdf_path)
                print(f"   测试文件已清理")
            except:
                pass

            return True
        else:
            print(f"[FAIL] PDF generation failed")
            return False

    except Exception as e:
        print(f"[ERROR] PDF generation exception: {e}")
        return False

def test_sftp_upload(settings):
    """测试SFTP上传"""
    print("\n" + "=" * 60)
    print("[5/5] 测试SFTP上传")
    print("=" * 60)

    try:
        import sys
        sys.path.append('.')
        from src.uploader.sftp_client import SFTPClient

        # 创建测试文件
        test_file = "test_sftp_upload.txt"
        with open(test_file, 'w') as f:
            f.write("test content")

        # 测试上传
        with SFTPClient() as sftp:
            test_remote_path = f"{settings.wxchat_sftp_remote_path}/test_upload.txt"

            print(f"测试上传到: {test_remote_path}")
            success = sftp.upload_file(test_file, test_remote_path)

            if success:
                print(f"[OK] SFTP upload successful")
            else:
                print(f"[FAIL] SFTP upload failed")

        # 清理测试文件
        try:
            os.unlink(test_file)
        except:
            pass

        return success

    except Exception as e:
        print(f"[ERROR] SFTP test exception: {e}")
        return False

def main():
    print("[Diagnostic] baidu-download.exe --wxchat Flow Test Tool")
    print("=" * 60)

    # 1. 测试配置
    settings = test_config()
    if not settings:
        print("\n[FAIL] Config load failed, cannot continue testing")
        return 1

    # 2. 测试数据库连接
    articles = test_database_connection(settings)
    if not articles:
        print("\n[FAIL] Database connection failed, cannot continue testing")
        return 1

    # 3. 测试URL生成
    url = test_url_generation(settings, articles)
    if not url:
        print("\n[FAIL] URL generation failed, cannot continue testing")
        return 1

    # 4. 测试PDF生成
    pdf_success = test_pdf_generation(settings, url)
    if not pdf_success:
        print("\n[WARNING] PDF generation failed, this is the main problem!")
        print("   原因可能是:")
        print("   1. Playwright 浏览器未安装")
        print("   2. 网络连接问题")
        print("   3. 微信文章访问受限")

    # 5. 测试SFTP上传
    sftp_success = test_sftp_upload(settings)
    if not sftp_success:
        print("\n[WARNING] SFTP upload failed")
        print("   原因可能是:")
        print("   1. SFTP服务器连接失败")
        print("   2. 权限不足")

    # 总结
    print("\n" + "=" * 60)
    print("诊断结果总结:")
    print("=" * 60)

    results = {
        "配置加载": settings is not None,
        "数据库连接": articles is not None,
        "URL生成": url is not None,
        "PDF生成": pdf_success,
        "SFTP上传": sftp_success
    }

    for step, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {step}")

    all_success = all(results.values())
    if all_success:
        print("\n[SUCCESS] All tests passed! The flow should work normally.")
        print("   Run command: baidu-download.exe --wxchat")
    else:
        failed_steps = [step for step, success in results.items() if not success]
        print(f"\n[FAIL] The following steps failed: {', '.join(failed_steps)}")
        print("   Please fix these issues and try again.")

    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main())