#!/usr/bin/env python3
"""
RepodataParser - 用于解析Fedora仓库数据的简化版本
基于Repology的RepodataParser实现
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import re


class Package:
    """简化的包数据结构"""
    
    def __init__(self):
        self.name: Optional[str] = None
        self.version: Optional[str] = None
        self.release: Optional[str] = None
        self.epoch: Optional[str] = None
        self.arch: Optional[str] = None
        self.summary: Optional[str] = None
        self.url: Optional[str] = None
        self.license: Optional[str] = None
        self.group: Optional[str] = None
        self.packager: Optional[str] = None
        self.sourcerpm: Optional[str] = None
        self.binnames: List[str] = []
        self.is_src: bool = False
        self.subrepo: Optional[str] = None  # 子仓库标识（如release/updates）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'version': self.version,
            'release': self.release,
            'epoch': self.epoch,
            'arch': self.arch,
            'summary': self.summary,
            'url': self.url,
            'license': self.license,
            'group': self.group,
            'packager': self.packager,
            'sourcerpm': self.sourcerpm,
            'binnames': self.binnames,
            'is_src': self.is_src,
            'subrepo': self.subrepo
        }


class RepodataParser:
    """解析Fedora仓库数据的解析器"""
    
    def __init__(self, src: bool = True, binary: bool = False, vertags: Optional[List[str]] = None):
        self.src = src
        self.binary = binary
        self.vertags = vertags or ['fc']
    
    def parse(self, xml_file_path: str) -> List[Package]:
        """
        解析XML文件并返回包列表
        
        Args:
            xml_file_path: XML文件路径
            
        Returns:
            List[Package]: 解析后的包列表
        """
        packages = []
        
        try:
            # 解析XML文件
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            
            # 定义命名空间
            namespaces = {
                'common': 'http://linux.duke.edu/metadata/common',
                'rpm': 'http://linux.duke.edu/metadata/rpm'
            }
            
            # 查找所有包元素
            package_elements = root.findall('.//common:package', namespaces)
            
            print(f"找到 {len(package_elements)} 个包")
            
            for pkg_element in package_elements:
                try:
                    package = self._parse_package(pkg_element, namespaces)
                    if package:
                        packages.append(package)
                except Exception as e:
                    print(f"解析包时出错: {e}")
                    continue
            
            print(f"成功解析 {len(packages)} 个包")
            
        except Exception as e:
            print(f"解析XML文件失败: {e}")
        
        return packages
    
    def _parse_package(self, pkg_element: ET.Element, namespaces: Dict[str, str]) -> Optional[Package]:
        """解析单个包元素"""
        package = Package()
        
        # 获取包名
        name_elem = pkg_element.find('common:name', namespaces)
        if name_elem is None or name_elem.text is None:
            return None
        package.name = name_elem.text.strip()
        
        # 检查包名是否包含未展开的宏
        if '%{' in package.name:
            print(f"跳过包含未展开宏的包名: {package.name}")
            return None
        
        # 获取架构
        arch_elem = pkg_element.find('common:arch', namespaces)
        if arch_elem is None or arch_elem.text is None:
            return None
        package.arch = arch_elem.text.strip()
        
        # 判断是否为源码包
        package.is_src = (package.arch == 'src')
        
        # 根据配置决定是否处理此包
        if package.is_src and not self.src:
            return None
        if not package.is_src and not self.binary:
            return None
        
        # 获取版本信息
        version_elem = pkg_element.find('common:version', namespaces)
        if version_elem is not None:
            package.epoch = version_elem.get('epoch', '0')
            package.version = version_elem.get('ver', '')
            package.release = version_elem.get('rel', '')
        
        # 获取其他信息
        summary_elem = pkg_element.find('common:summary', namespaces)
        if summary_elem is not None and summary_elem.text:
            package.summary = summary_elem.text.strip()
        
        url_elem = pkg_element.find('common:url', namespaces)
        if url_elem is not None and url_elem.text:
            package.url = url_elem.text.strip()
        
        # 获取RPM特定信息
        rpm_license = pkg_element.find('common:format/rpm:license', namespaces)
        if rpm_license is not None and rpm_license.text:
            package.license = rpm_license.text.strip()
        
        rpm_group = pkg_element.find('common:format/rpm:group', namespaces)
        if rpm_group is not None and rpm_group.text:
            package.group = rpm_group.text.strip()
        
        packager_elem = pkg_element.find('common:packager', namespaces)
        if packager_elem is not None and packager_elem.text:
            package.packager = packager_elem.text.strip()
        
        # 对于二进制包，获取源码包名
        if not package.is_src:
            sourcerpm_elem = pkg_element.find('common:format/rpm:sourcerpm', namespaces)
            if sourcerpm_elem is not None and sourcerpm_elem.text:
                package.sourcerpm = sourcerpm_elem.text.strip()
        
        # 获取Provides信息（二进制包名）
        if not package.is_src:
            provides_elements = pkg_element.findall('common:format/rpm:provides/rpm:entry', namespaces)
            for provide_elem in provides_elements:
                provide_name = provide_elem.get('name', '')
                # 过滤掉包含括号和特殊字符的provides
                if provide_name and '(' not in provide_name and ')' not in provide_name:
                    # 检查是否有版本信息
                    if provide_elem.get('ver') and provide_elem.get('rel'):
                        package.binnames.append(provide_name)
        
        return package
    
    def _parse_rpm_version(self, version: str, release: str) -> tuple[str, int]:
        """解析RPM版本信息"""
        # 简化的版本解析，实际实现会更复杂
        flags = 0
        
        # 检查版本标签
        for vertag in self.vertags:
            if vertag in release:
                flags |= 1  # 简化的标志位
        
        return version, flags


def nevra_parse(nevra_string: str) -> tuple[str, str, str, str, str]:
    """解析NEVRA字符串 (Name-Epoch-Version-Release-Architecture)"""
    # 简化的NEVRA解析
    parts = nevra_string.rsplit('.', 1)
    if len(parts) == 2:
        name_part, arch = parts
    else:
        name_part = nevra_string
        arch = ''
    
    # 进一步解析name部分
    # 这里需要更复杂的解析逻辑
    return name_part, '', '', '', arch
