#!/usr/bin/env python3
"""
OpenHarmonyParser - 用于解析OpenHarmony仓库数据的解析器
支持多种parser类型：OHPMParser, OhpmIndexParser, OHPMJsonParser, GitCodeProjectsParser, GiteeRepoParser(已废弃)
对应 openharmony.yaml 中的数据源
"""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup


class OpenHarmonyPackage:
    """OpenHarmony包数据结构"""
    
    def __init__(self):
        self.name: Optional[str] = None
        self.srcname: Optional[str] = None  # 源名称（用于链接）
        self.version: Optional[str] = None
        self.description: Optional[str] = None
        self.author: Optional[str] = None
        self.maintainers: List[str] = []
        self.homepage: Optional[str] = None
        self.repository: Optional[str] = None
        self.license: Optional[str] = None
        self.licenses: List[str] = []  # 支持多个许可证
        self.keywords: List[str] = []
        self.categories: List[str] = []
        self.dependencies: Dict[str, str] = {}
        self.dev_dependencies: Dict[str, str] = {}
        self.download_count: int = 0
        self.star_count: int = 0
        self.fork_count: int = 0
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None
        self.package_type: str = 'ohpm'  # 'ohpm', 'ohpm-api', 或 'gitee'
        self.subrepo: Optional[str] = None  # 子仓库标识
        self.detail_url: Optional[str] = None  # 详情页URL
        self.is_official: bool = False
        self.bundle_json: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'srcname': self.srcname or self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'maintainers': self.maintainers,
            'homepage': self.homepage,
            'repository': self.repository,
            'license': self.license,
            'licenses': self.licenses,
            'keywords': self.keywords,
            'categories': self.categories,
            'dependencies': self.dependencies,
            'dev_dependencies': self.dev_dependencies,
            'download_count': self.download_count,
            'star_count': self.star_count,
            'fork_count': self.fork_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'package_type': self.package_type,
            'subrepo': self.subrepo,
            'detail_url': self.detail_url,
            'is_official': self.is_official
        }


class BaseParser:
    """基础解析器类"""
    
    def __init__(self, subrepo: Optional[str] = None, vertags: Optional[str] = None):
        self.subrepo = subrepo
        self.vertags = vertags
        self.official_prefixes = [
            'openharmony',
            'harmony',
            'hmos',
            'ohos',
            '@ohos',
            '@system'
        ]
    
    def parse(self, file_path: str) -> List[OpenHarmonyPackage]:
        """解析文件并返回包列表"""
        raise NotImplementedError("Subclasses must implement parse()")
    
    def _is_official_package(self, package_name: str) -> bool:
        """判断是否为官方包"""
        name_lower = package_name.lower()
        return any(name_lower.startswith(prefix.lower()) for prefix in self.official_prefixes)


class OHPMParser(BaseParser):
    """
    OHPM Landscape 页面解析器
    对应 yaml 中的 ohpm_landscape source
    解析组件卡片并提取详情页URLs
    """
    
    def parse(self, file_path: str) -> List[OpenHarmonyPackage]:
        """解析OHPM Landscape HTML页面"""
        packages = []
        
        try:
            print(f"[OHPMParser] 正在解析文件: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找组件卡片
            # 注意：实际的选择器需要根据真实的HTML结构调整
            component_cards = soup.find_all('div', class_='component-card')
            
            if not component_cards:
                # 尝试其他可能的选择器
                component_cards = soup.find_all('div', class_='package-card')
            
            if not component_cards:
                # 尝试通过链接查找
                component_links = soup.find_all('a', href=re.compile(r'/cn/detail/'))
                print(f"[OHPMParser] 找到 {len(component_links)} 个组件链接")
                
                for link in component_links:
                    package = self._parse_component_link(link)
                    if package:
                        packages.append(package)
            else:
                print(f"[OHPMParser] 找到 {len(component_cards)} 个组件卡片")
                
                for card in component_cards:
                    package = self._parse_component_card(card)
                    if package:
                        packages.append(package)
            
            print(f"[OHPMParser] 成功解析 {len(packages)} 个包")
            
        except Exception as e:
            print(f"[OHPMParser] 解析失败: {e}")
        
        return packages
    
    def _parse_component_card(self, card) -> Optional[OpenHarmonyPackage]:
        """解析组件卡片"""
        package = OpenHarmonyPackage()
        package.package_type = 'ohpm'
        package.subrepo = self.subrepo
        
        try:
            # 提取包名
            name_elem = card.find(['h3', 'h4', 'div'], class_=re.compile(r'(name|title)'))
            if name_elem:
                package.name = name_elem.get_text(strip=True)
                package.srcname = package.name
            
            # 提取描述
            desc_elem = card.find(['p', 'div'], class_=re.compile(r'(desc|description)'))
            if desc_elem:
                package.description = desc_elem.get_text(strip=True)
            
            # 提取详情页链接
            link_elem = card.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                if href.startswith('/'):
                    package.detail_url = f"https://ohpm.openharmony.cn/#/cn/detail/{package.name}"
                else:
                    package.detail_url = href
                
                # 从URL中提取包名
                match = re.search(r'/detail/([^/\?#]+)', href)
                if match:
                    package.srcname = match.group(1)
            
            # 检查是否为官方包
            if package.name:
                package.is_official = self._is_official_package(package.name)
            
            return package if package.name else None
            
        except Exception as e:
            print(f"[OHPMParser] 解析卡片时出错: {e}")
            return None
    
    def _parse_component_link(self, link) -> Optional[OpenHarmonyPackage]:
        """从链接解析组件信息"""
        package = OpenHarmonyPackage()
        package.package_type = 'ohpm'
        package.subrepo = self.subrepo
        
        try:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 从URL中提取包名
            match = re.search(r'/detail/([^/\?#]+)', href)
            if match:
                package.srcname = match.group(1)
                package.name = package.srcname
            
            # 使用链接文本作为名称
            if text and not package.name:
                package.name = text
                package.srcname = text
            
            # 构建详情页URL
            if package.srcname:
                package.detail_url = f"https://ohpm.openharmony.cn/#/cn/detail/{package.srcname}"
            
            # 检查是否为官方包
            if package.name:
                package.is_official = self._is_official_package(package.name)
            
            return package if package.name else None
            
        except Exception as e:
            print(f"[OHPMParser] 解析链接时出错: {e}")
            return None


class OhpmIndexParser(BaseParser):
    """
    OHPM索引解析器 - 解析 packages-index.json
    对应 yaml 中的 ohpm_source_index source
    解析预构建的 JSON 索引文件
    """
    
    def parse(self, file_path: str) -> List[OpenHarmonyPackage]:
        """解析OHPM索引JSON文件"""
        packages = []
        
        try:
            print(f"[OhpmIndexParser] 正在解析文件: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理索引数据结构
            # 可能的格式: {"packages": [...]} 或直接是数组 [...]
            package_list = []
            if isinstance(data, dict):
                package_list = data.get('packages', data.get('data', []))
            elif isinstance(data, list):
                package_list = data
            
            print(f"[OhpmIndexParser] 找到 {len(package_list)} 个包")
            
            for pkg_data in package_list:
                package = self._parse_package(pkg_data)
                if package:
                    packages.append(package)
            
            print(f"[OhpmIndexParser] 成功解析 {len(packages)} 个包")
            
        except Exception as e:
            print(f"[OhpmIndexParser] 解析失败: {e}")
        
        return packages
    
    def _parse_package(self, pkg_data: Dict[str, Any]) -> Optional[OpenHarmonyPackage]:
        """解析单个包数据"""
        package = OpenHarmonyPackage()
        package.package_type = 'ohpm-index'
        package.subrepo = self.subrepo
        
        # 基本信息
        package.name = pkg_data.get('name', '').strip()
        if not package.name:
            return None
        
        package.srcname = package.name
        package.version = pkg_data.get('version', pkg_data.get('latestVersion', '')).strip()
        package.description = pkg_data.get('description', '').strip()
        
        # 作者信息
        author_info = pkg_data.get('author', {})
        if isinstance(author_info, dict):
            package.author = author_info.get('name', '').strip()
        elif isinstance(author_info, str):
            package.author = author_info.strip()
        
        # 链接信息
        package.homepage = pkg_data.get('homepage', f"https://ohpm.openharmony.cn/#/cn/detail/{package.srcname}").strip()
        
        repository = pkg_data.get('repository', {})
        if isinstance(repository, dict):
            package.repository = repository.get('url', '').strip()
        elif isinstance(repository, str):
            package.repository = repository.strip()
        
        # 许可证
        license_data = pkg_data.get('license', '')
        if isinstance(license_data, str) and license_data:
            package.license = license_data.strip()
            package.licenses = [package.license]
        elif isinstance(license_data, list):
            package.licenses = [lic.strip() for lic in license_data if isinstance(lic, str)]
            if package.licenses:
                package.license = package.licenses[0]
        
        # 关键词和分类
        keywords = pkg_data.get('keywords', [])
        if isinstance(keywords, list):
            package.keywords = [kw.strip() for kw in keywords if isinstance(kw, str)]
        
        # 检查是否为官方包
        package.is_official = self._is_official_package(package.name)
        
        return package


class OHPMJsonParser(BaseParser):
    """
    OHPM API JSON解析器
    对应 yaml 中的 ohpm_api source
    收集包名、版本、描述、许可证、更新时间
    """
    
    def parse(self, file_path: str) -> List[OpenHarmonyPackage]:
        """解析OHPM API JSON数据"""
        packages = []
        
        try:
            print(f"[OHPMJsonParser] 正在解析文件: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取包列表
            package_list = data.get('packages', [])
            
            print(f"[OHPMJsonParser] 找到 {len(package_list)} 个包")
            
            for pkg_data in package_list:
                package = self._parse_package(pkg_data)
                if package:
                    packages.append(package)
            
            print(f"[OHPMJsonParser] 成功解析 {len(packages)} 个包")
            
        except Exception as e:
            print(f"[OHPMJsonParser] 解析失败: {e}")
        
        return packages
    
    def _parse_package(self, pkg_data: Dict[str, Any]) -> Optional[OpenHarmonyPackage]:
        """解析单个包数据"""
        package = OpenHarmonyPackage()
        package.package_type = 'ohpm-api'
        package.subrepo = self.subrepo
        
        # 基本信息
        package.name = pkg_data.get('name', '').strip()
        if not package.name:
            return None
        
        package.srcname = package.name
        
        # 版本信息
        package.version = pkg_data.get('version', '').strip()
        if not package.version:
            package.version = pkg_data.get('latestVersion', '').strip()
        
        # 描述信息
        package.description = pkg_data.get('description', '').strip()
        
        # 作者信息
        author_info = pkg_data.get('author', {})
        if isinstance(author_info, dict):
            package.author = author_info.get('name', '').strip()
        elif isinstance(author_info, str):
            package.author = author_info.strip()
        
        # 维护者信息
        maintainers = pkg_data.get('maintainers', [])
        if isinstance(maintainers, list):
            for maintainer in maintainers:
                if isinstance(maintainer, dict):
                    name = maintainer.get('name', '').strip()
                    if name:
                        package.maintainers.append(name)
                elif isinstance(maintainer, str):
                    package.maintainers.append(maintainer.strip())
        
        # 主页链接
        package.homepage = pkg_data.get('homepage', '').strip()
        if not package.homepage:
            package.homepage = f"https://ohpm.openharmony.cn/#/cn/detail/{package.srcname}"
        
        # 仓库链接
        repository = pkg_data.get('repository', {})
        if isinstance(repository, dict):
            package.repository = repository.get('url', '').strip()
        elif isinstance(repository, str):
            package.repository = repository.strip()
        
        # 许可证
        license_data = pkg_data.get('license', '')
        if isinstance(license_data, str):
            package.license = license_data.strip()
            if package.license:
                package.licenses = [package.license]
        elif isinstance(license_data, list):
            package.licenses = [lic.strip() for lic in license_data if isinstance(lic, str)]
            if package.licenses:
                package.license = package.licenses[0]
        
        # 关键词
        keywords = pkg_data.get('keywords', [])
        if isinstance(keywords, list):
            package.keywords = [kw.strip() for kw in keywords if isinstance(kw, str)]
        
        # 分类
        categories = pkg_data.get('categories', [])
        if isinstance(categories, list):
            package.categories = [cat.strip() for cat in categories if isinstance(cat, str)]
        
        # 依赖信息
        dependencies = pkg_data.get('dependencies', {})
        if isinstance(dependencies, dict):
            package.dependencies = dependencies
        
        dev_dependencies = pkg_data.get('devDependencies', {})
        if isinstance(dev_dependencies, dict):
            package.dev_dependencies = dev_dependencies
        
        # 统计信息
        package.download_count = pkg_data.get('downloadCount', 0)
        if not package.download_count:
            package.download_count = pkg_data.get('downloads', 0)
        
        # 时间信息
        package.created_at = pkg_data.get('createdAt', pkg_data.get('createTime', ''))
        package.updated_at = pkg_data.get('updatedAt', pkg_data.get('updateTime', ''))
        
        # 检查是否为官方包
        package.is_official = self._is_official_package(package.name)
        
        return package


class GitCodeProjectsParser(BaseParser):
    """
    GitCode仓库解析器
    对应 yaml 中的 gitcode_tpc source
    解析 GitCode 网页上的 openharmony-tpc 组织下的所有仓库
    """
    
    def parse(self, file_path: str) -> List[OpenHarmonyPackage]:
        """解析GitCode网页"""
        packages = []
        
        try:
            print(f"[GitCodeProjectsParser] 正在解析文件: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找仓库卡片或链接
            # GitCode 的结构可能与 Gitee 不同，这里提供多种选择器尝试
            repo_items = []
            
            # 尝试1: 查找仓库链接
            repo_links = soup.find_all('a', href=re.compile(r'/openharmony-tpc/[^/]+/?$'))
            if repo_links:
                print(f"[GitCodeProjectsParser] 找到 {len(repo_links)} 个仓库链接")
                for link in repo_links:
                    package = self._parse_repo_link(link, soup)
                    if package:
                        packages.append(package)
            
            # 尝试2: 查找仓库列表项
            if not packages:
                repo_items = soup.find_all('div', class_=re.compile(r'(repo|repository|project).*item', re.I))
                if repo_items:
                    print(f"[GitCodeProjectsParser] 找到 {len(repo_items)} 个仓库项")
                    for item in repo_items:
                        package = self._parse_repo_item(item)
                        if package:
                            packages.append(package)
            
            # 去重（基于仓库名）
            unique_packages = {}
            for pkg in packages:
                if pkg.name not in unique_packages:
                    unique_packages[pkg.name] = pkg
            
            packages = list(unique_packages.values())
            print(f"[GitCodeProjectsParser] 成功解析 {len(packages)} 个仓库")
            
        except Exception as e:
            print(f"[GitCodeProjectsParser] 解析失败: {e}")
        
        return packages
    
    def _parse_repo_link(self, link, soup) -> Optional[OpenHarmonyPackage]:
        """从链接解析仓库信息"""
        package = OpenHarmonyPackage()
        package.package_type = 'gitcode'
        package.subrepo = self.subrepo
        package.is_official = True
        
        try:
            href = link.get('href', '')
            
            # 从URL中提取仓库名
            match = re.search(r'/openharmony-tpc/([^/\?#]+)', href)
            if match:
                package.name = match.group(1)
                package.srcname = package.name
            
            # 构建完整URL
            if href.startswith('/'):
                package.repository = f"https://gitcode.com{href}"
            else:
                package.repository = href
            
            # 尝试从链接文本或附近元素获取描述
            text = link.get_text(strip=True)
            if text and text != package.name:
                package.description = text
            
            # 查找相邻的描述元素
            parent = link.parent
            if parent:
                desc_elem = parent.find(['p', 'div', 'span'], class_=re.compile(r'(desc|description)', re.I))
                if desc_elem:
                    package.description = desc_elem.get_text(strip=True)
            
            # 设置默认版本
            package.version = '1.0.0'
            
            return package if package.name else None
            
        except Exception as e:
            print(f"[GitCodeProjectsParser] 解析链接时出错: {e}")
            return None
    
    def _parse_repo_item(self, item) -> Optional[OpenHarmonyPackage]:
        """解析仓库项元素"""
        package = OpenHarmonyPackage()
        package.package_type = 'gitcode'
        package.subrepo = self.subrepo
        package.is_official = True
        
        try:
            # 查找仓库名和链接
            name_link = item.find('a', href=re.compile(r'/openharmony-tpc/'))
            if name_link:
                href = name_link.get('href', '')
                match = re.search(r'/openharmony-tpc/([^/\?#]+)', href)
                if match:
                    package.name = match.group(1)
                    package.srcname = package.name
                
                if href.startswith('/'):
                    package.repository = f"https://gitcode.com{href}"
                else:
                    package.repository = href
            
            # 查找描述
            desc_elem = item.find(['p', 'div', 'span'], class_=re.compile(r'(desc|description)', re.I))
            if desc_elem:
                package.description = desc_elem.get_text(strip=True)
            
            # 查找星标数
            star_elem = item.find(text=re.compile(r'\d+\s*star', re.I))
            if star_elem:
                star_match = re.search(r'(\d+)', star_elem)
                if star_match:
                    package.star_count = int(star_match.group(1))
            
            # 查找fork数
            fork_elem = item.find(text=re.compile(r'\d+\s*fork', re.I))
            if fork_elem:
                fork_match = re.search(r'(\d+)', fork_elem)
                if fork_match:
                    package.fork_count = int(fork_match.group(1))
            
            # 设置默认版本
            package.version = '1.0.0'
            
            return package if package.name else None
            
        except Exception as e:
            print(f"[GitCodeProjectsParser] 解析仓库项时出错: {e}")
            return None


class GiteeRepoParser(BaseParser):
    """
    Gitee仓库解析器（已废弃，保留用于兼容）
    对应 yaml 中的 gitee_tpc source
    使用 Gitee API 列出 openharmony-tpc 组织下的所有仓库
    """
    
    def parse(self, file_path: str) -> List[OpenHarmonyPackage]:
        """解析GitCode/Gitee API JSON数据（容错多种字段名）"""
        packages = []
        
        try:
            print(f"[GiteeRepoParser] 正在解析文件: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取仓库列表
            repo_list = []
            if isinstance(data, dict):
                # 标准化容器键
                repo_list = (
                    data.get('repos') or
                    data.get('data') or
                    data.get('items') or
                    data.get('list') or
                    []
                )
                # 有时上面键里又包了一层
                if isinstance(repo_list, dict):
                    repo_list = repo_list.get('repos') or repo_list.get('items') or repo_list.get('list') or []
            elif isinstance(data, list):
                repo_list = data
            
            print(f"[GiteeRepoParser] 找到 {len(repo_list)} 个仓库")
            
            for repo_data in repo_list:
                package = self._parse_repo(repo_data)
                if package:
                    packages.append(package)
            
            print(f"[GiteeRepoParser] 成功解析 {len(packages)} 个包")
            
        except Exception as e:
            print(f"[GiteeRepoParser] 解析失败: {e}")
        
        return packages
    
    def _parse_repo(self, repo_data: Dict[str, Any]) -> Optional[OpenHarmonyPackage]:
        """解析单个Gitee仓库"""
        package = OpenHarmonyPackage()
        package.package_type = 'gitee'
        package.subrepo = self.subrepo
        
        # 基本信息
        name = repo_data.get('name') or repo_data.get('path') or ''
        package.name = (name or '').strip()
        if not package.name:
            return None
        
        package.srcname = package.name
        package.is_official = True  # openharmony-tpc组织下的都是官方仓库
        
        # 全名（包含组织名）
        full_name = repo_data.get('full_name') or repo_data.get('path_with_namespace') or ''
        
        # 描述信息
        package.description = (repo_data.get('description') or '').strip()
        
        # 作者/所有者信息
        owner = repo_data.get('owner', {})
        if isinstance(owner, dict):
            package.author = (owner.get('login') or owner.get('name') or '').strip()
        
        # 链接信息
        package.homepage = (repo_data.get('homepage') or '').strip()
        package.repository = (repo_data.get('html_url') or repo_data.get('web_url') or '').strip()
        if not package.repository and full_name:
            package.repository = f"https://gitcode.com/{full_name}"
        
        # 许可证
        license_info = repo_data.get('license', {})
        if isinstance(license_info, dict):
            package.license = license_info.get('spdx_id', '').strip()
            if not package.license:
                package.license = license_info.get('name', '').strip()
            if package.license:
                package.licenses = [package.license]
        
        # 统计信息
        package.star_count = repo_data.get('stargazers_count') or repo_data.get('star_count') or repo_data.get('watchers_count') or 0
        package.fork_count = repo_data.get('forks_count') or 0
        
        # 时间信息
        package.created_at = repo_data.get('created_at') or repo_data.get('createdAt') or ''
        package.updated_at = repo_data.get('updated_at') or repo_data.get('last_activity_at') or repo_data.get('updateTime') or ''
        
        # 从仓库名推断版本
        version_match = re.search(r'[_-]v?(\d+\.\d+(?:\.\d+)?)', package.name)
        if version_match:
            package.version = version_match.group(1)
        else:
            # 使用更新时间作为版本号的一部分
            if package.updated_at:
                try:
                    # 提取年月作为版本号
                    date_match = re.search(r'(\d{4})-(\d{2})', package.updated_at)
                    if date_match:
                        package.version = f"{date_match.group(1)}.{date_match.group(2)}.0"
                    else:
                        package.version = '1.0.0'
                except:
                    package.version = '1.0.0'
            else:
                package.version = '1.0.0'
        
        # 提取语言信息作为关键词
        language = repo_data.get('language', '')
        if language:
            package.keywords.append(language)
        
        # 从描述中提取关键词
        if package.description:
            keywords = re.findall(
                r'\b(?:OpenHarmony|HarmonyOS|OHOS|鸿蒙|组件|模块|库|框架|工具|' +
                r'JavaScript|TypeScript|JS|TS)\b',
                package.description,
                re.IGNORECASE
            )
            package.keywords.extend(list(set(keywords)))
        
        # 去重关键词
        package.keywords = list(set(package.keywords))
        
        return package


def main():
    """测试函数 - 测试三种parser"""
    import os
    import json
    
    print("=" * 60)
    print("OpenHarmony Parser 测试")
    print("=" * 60)
    
    # 测试1: OHPMParser - 解析Landscape页面
    print("\n测试1: OHPMParser - OHPM Landscape 页面")
    print("-" * 60)
    if os.path.exists('generated/test/ohpm_landscape.html'):
        parser1 = OHPMParser(subrepo='ohpm')
        packages1 = parser1.parse('generated/test/ohpm_landscape.html')
        print(f"✓ 解析到 {len(packages1)} 个组件")
        
        if packages1:
            print(f"\n示例组件:")
            for i, pkg in enumerate(packages1[:3], 1):
                print(f"  {i}. {pkg.name}")
                print(f"     描述: {pkg.description}")
                print(f"     详情页: {pkg.detail_url}")
    else:
        print("✗ 测试文件不存在: generated/test/ohpm_landscape.html")
    
    # 测试2: OHPMJsonParser - 解析OHPM API JSON
    print("\n测试2: OHPMJsonParser - OHPM API JSON")
    print("-" * 60)
    if os.path.exists('generated/test/ohpm_api_packages.json'):
        parser2 = OHPMJsonParser(subrepo='ohpm-api', vertags='ohpm')
        packages2 = parser2.parse('generated/test/ohpm_api_packages.json')
        print(f"✓ 解析到 {len(packages2)} 个包")
        
        if packages2:
            print(f"\n示例包:")
            for i, pkg in enumerate(packages2[:3], 1):
                print(f"  {i}. {pkg.name} v{pkg.version}")
                print(f"     描述: {pkg.description}")
                print(f"     许可证: {pkg.license}")
                print(f"     更新时间: {pkg.updated_at}")
        
        # 导出解析结果
        output_file = 'generated/test/ohpm_api_parsed.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([pkg.to_dict() for pkg in packages2], f, ensure_ascii=False, indent=2)
        print(f"\n✓ 解析结果已保存到: {output_file}")
    else:
        print("✗ 测试文件不存在: generated/test/ohpm_api_packages.json")
    
    # 测试3: GitCodeProjectsParser - 解析GitCode网页
    print("\n测试3: GitCodeProjectsParser - GitCode TPC 网页")
    print("-" * 60)
    if os.path.exists('generated/test/gitcode_tpc_repos.html'):
        parser3 = GitCodeProjectsParser(subrepo='gitcode-tpc')
        packages3 = parser3.parse('generated/test/gitcode_tpc_repos.html')
        print(f"✓ 解析到 {len(packages3)} 个仓库")
        
        if packages3:
            print(f"\n示例仓库:")
            for i, pkg in enumerate(packages3[:3], 1):
                print(f"  {i}. {pkg.name} v{pkg.version}")
                print(f"     描述: {pkg.description}")
                print(f"     Stars: {pkg.star_count}")
                print(f"     仓库: {pkg.repository}")
        
        # 导出解析结果
        output_file = 'generated/test/gitcode_tpc_parsed.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([pkg.to_dict() for pkg in packages3], f, ensure_ascii=False, indent=2)
        print(f"\n✓ 解析结果已保存到: {output_file}")
    else:
        print("✗ 测试文件不存在: generated/test/gitcode_tpc_repos.html")
    
    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
