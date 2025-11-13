#!/usr/bin/env python3
"""
OpenHarmonyFetcher - 用于获取OpenHarmony仓库数据的获取器
支持多种fetcher类型：WebpageFetcher, APIFetcher, APIBatchFetcher
对应 openharmony.yaml 中的数据源（支持 OHPM 和 GitCode）
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List
import time
from bs4 import BeautifulSoup


class BaseFetcher:
    """基础获取器类"""
    
    def __init__(self, url: str, fetch_timeout: int = 60):
        self.url = url
        self.fetch_timeout = fetch_timeout
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })

        # 如果提供了 GitCode 令牌，则自动附加到请求头（兼容两种方式）
        try:
            import os as _os
            _token = _os.getenv('GITCODE_TOKEN') or _os.getenv('GITCODE_PRIVATE_TOKEN')
            if _token:
                # 同时设置两种常见头部，后端会择一识别
                self.session.headers['Authorization'] = f'Bearer {_token}'
                self.session.headers['PRIVATE-TOKEN'] = _token
        except Exception:
            # 环境变量不可用时忽略
            pass
    
    def fetch(self, output_path: str) -> bool:
        """获取数据并保存到指定路径"""
        raise NotImplementedError("Subclasses must implement fetch()")


class WebpageFetcher(BaseFetcher):
    """
    网页抓取器 - 用于抓取网页内容（HTML、JSON等）
    对应 yaml 中的 WebpageFetcher
    """
    
    def fetch(self, output_path: str) -> bool:
        """抓取网页内容并保存"""
        try:
            print(f"[WebpageFetcher] 正在抓取页面: {self.url}")
            
            response = self.session.get(self.url, timeout=self.fetch_timeout)
            response.raise_for_status()
            
            # 保存HTML内容
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            file_size = os.path.getsize(output_path)
            print(f"[WebpageFetcher] 页面抓取成功，大小: {file_size} 字节")
            
            return True
            
        except Exception as e:
            print(f"[WebpageFetcher] 抓取失败: {e}")
            return False


class APIFetcher(BaseFetcher):
    """
    API抓取器 - 用于抓取 OHPM API 数据，支持分页
    对应 yaml 中的 ohpm_api source
    URL示例: https://ohpm.openharmony.cn/api/v1/packages/search?keyword=js&page=1&pageSize=100
    """
    
    def fetch(self, output_path: str) -> bool:
        """抓取API数据并保存为JSON"""
        try:
            print(f"[APIFetcher] 正在抓取API: {self.url}")
            
            all_packages = []
            page = 1
            max_pages = 100  # 最大页数限制
            
            while page <= max_pages:
                # 构建分页URL
                page_url = self._build_page_url(page)
                print(f"[APIFetcher] 正在获取第 {page} 页...")
                
                response = self.session.get(page_url, timeout=self.fetch_timeout)
                response.raise_for_status()
                
                data = response.json()
                
                # 解析响应格式
                packages = self._extract_packages(data)
                
                if not packages:
                    print(f"[APIFetcher] 第 {page} 页无数据，停止抓取")
                    break
                
                all_packages.extend(packages)
                print(f"[APIFetcher] 第 {page} 页获取到 {len(packages)} 个包")
                
                # 检查是否有更多数据
                if not self._has_more_pages(data, packages):
                    break
                
                page += 1
                time.sleep(0.5)  # 避免请求过快
            
            # 保存数据
            result = {
                'fetcher_type': 'APIFetcher',
                'source_url': self.url,
                'total_count': len(all_packages),
                'packages': all_packages,
                'fetch_time': time.time()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"[APIFetcher] 抓取完成，共 {len(all_packages)} 个包")
            return True
            
        except Exception as e:
            print(f"[APIFetcher] 抓取失败: {e}")
            return False
    
    def _build_page_url(self, page: int) -> str:
        """构建分页URL"""
        import re
        url = self.url
        
        # 替换或添加page参数
        if 'page=' in url:
            url = re.sub(r'page=\d+', f'page={page}', url)
        elif '?' in url:
            url = f"{url}&page={page}"
        else:
            url = f"{url}?page={page}"
        
        # 确保有pageSize参数
        if 'pageSize=' not in url and 'page_size=' not in url:
            url = f"{url}&pageSize=100"
        
        return url
    
    def _extract_packages(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从响应中提取包列表"""
        # 尝试多种可能的响应格式
        if 'data' in data:
            if isinstance(data['data'], list):
                return data['data']
            elif 'packages' in data['data']:
                return data['data']['packages']
            elif 'items' in data['data']:
                return data['data']['items']
        
        if 'packages' in data:
            return data['packages']
        
        if 'items' in data:
            return data['items']
        
        if isinstance(data, list):
            return data
        
        return []
    
    def _has_more_pages(self, data: Dict[str, Any], packages: List) -> bool:
        """判断是否还有更多页"""
        # 如果当前页没有数据，则没有更多页
        if not packages:
            return False
        
        # 检查total字段
        if 'total' in data:
            total = data['total']
            if 'data' in data and 'page' in data['data']:
                page = data['data']['page']
                page_size = data['data'].get('pageSize', 100)
                return page * page_size < total
        
        # 如果有pagination信息
        if 'pagination' in data:
            pagination = data['pagination']
            if 'hasMore' in pagination:
                return pagination['hasMore']
            if 'page' in pagination and 'totalPages' in pagination:
                return pagination['page'] < pagination['totalPages']
        
        # 默认：如果包数量等于页面大小，可能还有更多
        return len(packages) >= 100


class APIBatchFetcher(BaseFetcher):
    """
    批量API抓取器 - 用于抓取 GitCode API 数据
    对应 yaml 中的 gitcode_tpc source
    URL格式: https://gitcode.com/api/v5/orgs/openharmony-tpc/repos?per_page=100&page={page}
    支持 {page} 占位符
    """
    
    def fetch(self, output_path: str) -> bool:
        """抓取GitCode API数据（批量分页）"""
        try:
            print(f"[APIBatchFetcher] 正在抓取API: {self.url}")
            
            all_repos = []
            page = 1
            max_pages = 50  # 最大页数限制
            
            while page <= max_pages:
                # 替换URL中的{page}占位符
                page_url = self.url.replace('{page}', str(page))
                print(f"[APIBatchFetcher] 正在获取第 {page} 页...")
                
                response = self.session.get(page_url, timeout=self.fetch_timeout)
                response.raise_for_status()
                
                data = response.json()

                # 兼容多种顶层结构
                if isinstance(data, list):
                    repos = data
                elif isinstance(data, dict):
                    # 可能出现在 data / items / repos 等字段
                    repos = data.get('data') or data.get('items') or data.get('repos') or []
                    if isinstance(repos, dict):
                        # 某些 API 返回 { data: { list: [...] } }
                        repos = repos.get('list') or repos.get('items') or []
                else:
                    repos = []

                if not isinstance(repos, list):
                    print(f"[APIBatchFetcher] 无法识别的返回结构，跳过本页。")
                    repos = []

                if not repos:
                    print(f"[APIBatchFetcher] 第 {page} 页无数据，停止抓取")
                    break
                
                all_repos.extend(repos)
                print(f"[APIBatchFetcher] 第 {page} 页获取到 {len(repos)} 个仓库")
                
                # 如果返回的仓库数少于每页数量，说明是最后一页
                per_page = self._extract_per_page_from_url()
                if len(repos) < per_page:
                    break
                
                page += 1
                time.sleep(0.5)  # 避免请求过快
            
            # 保存数据
            result = {
                'fetcher_type': 'APIBatchFetcher',
                'source_url': self.url,
                'total_count': len(all_repos),
                'repos': all_repos,
                'fetch_time': time.time()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"[APIBatchFetcher] 抓取完成，共 {len(all_repos)} 个仓库")
            return True
            
        except Exception as e:
            print(f"[APIBatchFetcher] 抓取失败: {e}")
            return False
    
    def _extract_per_page_from_url(self) -> int:
        """从URL中提取每页数量"""
        import re
        match = re.search(r'per_page=(\d+)', self.url)
        if match:
            return int(match.group(1))
        return 100  # 默认值


# JsonFetcher 是 WebpageFetcher 的别名，用于语义上更清晰地表示获取JSON数据
class JsonFetcher(WebpageFetcher):
    """
    JSON文件抓取器 - 用于抓取JSON格式的数据文件
    对应 yaml 中的 JsonFetcher
    实际上是 WebpageFetcher 的别名
    """
    pass


class SeleniumFetcher:
    """
    Selenium网页抓取器 - 用于抓取JavaScript渲染的网页（SPA应用）
    适用于 GitCode 等单页应用
    
    需要安装: pip install selenium webdriver-manager
    """
    
    def __init__(self, url: str, wait_seconds: int = 10, headless: bool = True, fetch_timeout: int = 60):
        """
        Args:
            url: 要访问的URL
            wait_seconds: 等待页面加载的秒数
            headless: 是否使用无头模式（不显示浏览器窗口）
            fetch_timeout: 请求超时时间（兼容参数，Selenium不使用）
        """
        self.url = url
        self.wait_seconds = wait_seconds
        self.headless = headless
        self.fetch_timeout = fetch_timeout
    
    def fetch(self, output_path: str) -> bool:
        """
        使用 Selenium 获取完整渲染后的 HTML
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError as e:
            print(f"[SeleniumFetcher] ❌ 缺少依赖库: {e}")
            print("[SeleniumFetcher] 请运行: pip install selenium webdriver-manager")
            return False
        
        driver = None
        try:
            # 配置浏览器选项
            options = Options()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 创建浏览器实例
            print(f"[SeleniumFetcher] 🌐 正在启动 Chrome 浏览器...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # 访问页面
            print(f"[SeleniumFetcher] 🔗 正在访问: {self.url}")
            driver.get(self.url)
            
            # 等待页面加载
            print(f"[SeleniumFetcher] ⏳ 等待 {self.wait_seconds} 秒让页面完全加载...")
            time.sleep(self.wait_seconds)
            
            # 滚动页面以触发懒加载
            print("[SeleniumFetcher] 📜 滚动页面加载更多内容...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 获取渲染后的HTML
            html = driver.page_source
            
            # 保存HTML内容
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            file_size = os.path.getsize(output_path)
            print(f"[SeleniumFetcher] ✅ 页面抓取成功，大小: {file_size:,} 字节")
            
            # 可选：保存截图用于调试
            try:
                screenshot_path = output_path.replace('.html', '_screenshot.png')
                driver.save_screenshot(screenshot_path)
                print(f"[SeleniumFetcher] 📸 已保存页面截图到: {screenshot_path}")
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"[SeleniumFetcher] ❌ 抓取失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if driver:
                driver.quit()
                print("[SeleniumFetcher] 🔚 浏览器已关闭")


def main():
    """最小产物模式：不直接产出文件。请通过 start.py 调用 OpenHarmony 分析。"""
    print("OpenHarmony fetchers ready. Use start.py to run minimal artifact generation.")


if __name__ == "__main__":
    main()
