#!/usr/bin/env python3
"""
RepodataFetcher - 用于获取Fedora仓库数据的简化版本
基于Repology的RepodataFetcher实现
"""

import os
import xml.etree.ElementTree as ET
import requests
import gzip
import bz2
import lzma
import zstandard as zstd
from typing import Optional


class RepodataFetcher:
    """获取Fedora仓库数据的获取器"""
    
    def __init__(self, url: str, fetch_timeout: int = 60):
        self.url = url
        self.fetch_timeout = fetch_timeout
        self.primary_key = 'primary'
    
    def fetch(self, output_path: str) -> bool:
        """
        获取仓库数据并保存到指定路径
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            bool: 是否成功获取数据
        """
        try:
            # 确保URL以/结尾
            baseurl = self.url
            if not baseurl.endswith('/'):
                baseurl += '/'
            
            # 获取repomd.xml
            repomd_url = baseurl + 'repodata/repomd.xml'
            print(f"正在获取元数据: {repomd_url}")
            
            response = requests.get(repomd_url, timeout=self.fetch_timeout)
            response.raise_for_status()
            
            # 解析repomd.xml
            repomd = ET.fromstring(response.content)
            primary_element = repomd.find(f'.//{{http://linux.duke.edu/metadata/repo}}data[@type="{self.primary_key}"]')
            
            if primary_element is None:
                raise RuntimeError(f'无法在repomd.xml中找到<{self.primary_key}>元素')
            
            # 获取primary数据位置
            location_element = primary_element.find('./{http://linux.duke.edu/metadata/repo}location')
            if location_element is None:
                raise RuntimeError('无法在repomd.xml中找到<location>元素')
            
            # 构建完整URL
            repodata_url = baseurl + location_element.attrib['href']
            print(f"正在获取仓库数据: {repodata_url}")
            
            # 下载压缩的仓库数据
            response = requests.get(repodata_url, timeout=self.fetch_timeout)
            response.raise_for_status()
            
            # 根据文件扩展名确定压缩类型
            compression = None
            if repodata_url.endswith('.gz'):
                compression = 'gz'
            elif repodata_url.endswith('.xz'):
                compression = 'xz'
            elif repodata_url.endswith('.bz2'):
                compression = 'bz2'
            elif repodata_url.endswith('.zst'):
                compression = 'zstd'
            
            # 解压并保存数据
            self._decompress_and_save(response.content, output_path, compression)
            
            file_size = os.path.getsize(output_path)
            print(f"数据大小: {file_size} 字节")
            
            return True
            
        except Exception as e:
            print(f"获取仓库数据失败: {e}")
            return False
    
    def _decompress_and_save(self, data: bytes, output_path: str, compression: Optional[str]):
        """解压数据并保存到文件"""
        if compression == 'gz':
            decompressed_data = gzip.decompress(data)
        elif compression == 'xz':
            decompressed_data = lzma.decompress(data)
        elif compression == 'bz2':
            decompressed_data = bz2.decompress(data)
        elif compression == 'zstd':
            dctx = zstd.ZstdDecompressor()
            decompressed_data = dctx.decompress(data)
        else:
            decompressed_data = data
        
        with open(output_path, 'wb') as f:
            f.write(decompressed_data)
