#!/usr/bin/env python3
"""
统一入口脚本 - 支持OpenHarmony和Fedora仓库分析
"""
import argparse
import sys
import os
import json
from pathlib import Path

# 导入所有fetcher和parser类
from openharmony_fetcher import WebpageFetcher, JsonFetcher, APIFetcher, APIBatchFetcher, SeleniumFetcher
from openharmony_parser import OHPMParser, OhpmIndexParser, OHPMJsonParser, GitCodeProjectsParser, GiteeRepoParser
from repodata_fetcher import RepodataFetcher
from repodata_parser import RepodataParser


def analyze_openharmony(output_dir: str = "generated/openharmony", release: str = "stable"):
    """分析OpenHarmony仓库"""
    print("=" * 60)
    print("开始分析 OpenHarmony 仓库")
    print("=" * 60)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义数据源配置（基于openharmony.yaml）
    sources = [
        {
            'name': 'ohpm_source_index',
            'fetcher': JsonFetcher('https://ohpm.openharmony.cn/packages-index.json'),
            'parser': OhpmIndexParser(subrepo='ohpm-index', vertags='ohpm'),
            'output': 'ohpm_source_index.json'
        },
        {
            'name': 'tpc_mirror',
            'fetcher': APIBatchFetcher(
                url='https://api.gitcode.com/api/v5/orgs/OpenHarmony-TPC/repos?per_page=100&page={page}'
            ),
            'parser': GiteeRepoParser(subrepo='gitcode-tpc'),
            'output': 'gitcode_tpc_repos.json'
        }
    ]
    
    all_packages = []
    
    for source in sources:
        print(f"\n{'='*60}")
        print(f"处理数据源: {source['name']}")
        print(f"{'='*60}")
        
        # 步骤1: 获取数据
        print(f"\n1. 获取 {source['name']} 数据...")
        temp_file = os.path.join(output_dir, source['output'])
        
        try:
            if source['fetcher'].fetch(temp_file):
                print(f"   ✓ 数据已保存到: {temp_file}")
            else:
                print(f"   ✗ 获取失败，跳过此数据源")
                continue
        except Exception as e:
            print(f"   ✗ 获取失败: {e}")
            continue
        
        # 步骤2: 解析数据
        print(f"\n2. 解析 {source['name']} 数据...")
        try:
            packages = source['parser'].parse(temp_file)
            # 统一关联到 release 子仓库
            for pkg in packages:
                try:
                    pkg.subrepo = release
                except Exception:
                    pass
            print(f"   ✓ 解析到 {len(packages)} 个包")
            all_packages.extend(packages)
        except Exception as e:
            print(f"   ✗ 解析失败: {e}")
            continue
    
    # 步骤3: 合并并保存所有数据
    print(f"\n{'='*60}")
    print("保存合并结果")
    print(f"{'='*60}")
    
    # 输出文件名：openharmony_[release]_all_packages.json（Fedora风格字段）
    output_file = os.path.join(output_dir, f"openharmony_{release}_all_packages.json")
    
    try:
        # 转换为 Fedora 风格的字段结构
        def to_fedora_like(pkg):
            return {
                'name': getattr(pkg, 'name', None),
                'version': getattr(pkg, 'version', '') or '',
                'release': f"{release}.ohpm",
                'epoch': '0',
                'arch': 'src',
                'summary': getattr(pkg, 'description', None),
                'url': getattr(pkg, 'homepage', None) or getattr(pkg, 'repository', None),
                'license': getattr(pkg, 'license', None),
                'group': 'Unspecified',
                'packager': 'OpenHarmony Project',
                'sourcerpm': None,
                'binnames': [],
                'is_src': True,
                'subrepo': release
            }

        fedora_like = [to_fedora_like(pkg) for pkg in all_packages]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(fedora_like, f, ensure_ascii=False, indent=2)
        print(f"✓ 所有包数据已保存到: {output_file}")
    except Exception as e:
        print(f"✗ 保存失败: {e}")
        return False

    # 生成最简 openharmony_[release]_repodata.xml
    try:
        import xml.etree.ElementTree as ET
        from datetime import datetime
        repodata_root = ET.Element('repodata')
        ET.SubElement(repodata_root, 'channel').text = release
        ET.SubElement(repodata_root, 'count').text = str(len(all_packages))
        ET.SubElement(repodata_root, 'generated').text = datetime.utcnow().isoformat() + 'Z'
        sources_elem = ET.SubElement(repodata_root, 'sources')
        for src in sources:
            s = ET.SubElement(sources_elem, 'source')
            s.set('name', src['name'])
            try:
                s.set('url', getattr(src['fetcher'], 'url', '') or '')
            except Exception:
                s.set('url', '')
        tree = ET.ElementTree(repodata_root)
        repodata_file = os.path.join(output_dir, f"openharmony_{release}_repodata.xml")
        tree.write(repodata_file, encoding='utf-8', xml_declaration=True)
        print(f"✓ 元数据已保存到: {repodata_file}")
    except Exception as e:
        print(f"✗ 生成 repodata 失败: {e}")
        return False

    # 清理中间文件，仅保留最终两个产物
    try:
        for src in sources:
            temp_file = os.path.join(output_dir, src['output'])
            if os.path.exists(temp_file):
                os.remove(temp_file)
    except Exception:
        pass
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"总包数: {len(all_packages)}")
    print(f"输出目录: {output_dir}")
    
    # 按数据源统计
    source_stats = {}
    for pkg in all_packages:
        subrepo = pkg.subrepo or 'unknown'
        source_stats[subrepo] = source_stats.get(subrepo, 0) + 1
    
    print("\n数据源统计:")
    for source, count in source_stats.items():
        print(f"  - {source}: {count} 个包")
    
    return True


def analyze_fedora(output_dir: str = "generated/fedora", version: str = "41"):
    """分析Fedora仓库"""
    print("=" * 60)
    print(f"开始分析 Fedora {version} 仓库")
    print("=" * 60)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义数据源配置（基于fedora.yaml）
    # 使用固定的镜像源
    mirror = 'https://fr2.rpmfind.net/linux/fedora/linux'
    
    sources = [
        {
            'name': 'release',
            'fetcher': RepodataFetcher(f'{mirror}/releases/{version}/Everything/source/tree/'),
            'parser': RepodataParser(vertags='fc'),
            'subrepo': 'release'
        }
    ]
    
    # 如果不是rawhide版本，添加updates源
    if version != 'rawhide':
        sources.append({
            'name': 'updates',
            'fetcher': RepodataFetcher(f'{mirror}/updates/{version}/Everything/source/tree/'),
            'parser': RepodataParser(vertags='fc'),
            'subrepo': 'updates'
        })
    
    all_packages = []
    
    for source in sources:
        print(f"\n{'='*60}")
        print(f"处理数据源: {source['name']}")
        print(f"{'='*60}")
        
        # 步骤1: 获取数据
        print(f"\n1. 获取 {source['name']} 仓库数据...")
        temp_file = os.path.join(output_dir, f"fedora_{version}_{source['name']}_repodata.xml")
        
        try:
            if source['fetcher'].fetch(temp_file):
                print(f"   ✓ 数据已保存到: {temp_file}")
            else:
                print(f"   ✗ 获取失败，跳过此数据源")
                continue
        except Exception as e:
            print(f"   ✗ 获取失败: {e}")
            continue
        
        # 步骤2: 解析数据
        print(f"\n2. 解析 {source['name']} 仓库数据...")
        try:
            packages = source['parser'].parse(temp_file)
            print(f"   ✓ 解析到 {len(packages)} 个包")
            
            # 设置subrepo
            for pkg in packages:
                pkg.subrepo = source['subrepo']
            
            all_packages.extend(packages)
        except Exception as e:
            print(f"   ✗ 解析失败: {e}")
            continue
    
    # 步骤3: 合并并保存所有数据
    print(f"\n{'='*60}")
    print("保存合并结果")
    print(f"{'='*60}")
    
    output_file = os.path.join(output_dir, f"fedora_{version}_all_packages.json")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([pkg.to_dict() for pkg in all_packages], f, ensure_ascii=False, indent=2)
        print(f"✓ 所有包数据已保存到: {output_file}")
    except Exception as e:
        print(f"✗ 保存失败: {e}")
        return False
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("分析完成!")
    print("=" * 60)
    print(f"Fedora {version} 总包数: {len(all_packages)}")
    print(f"输出目录: {output_dir}")
    
    # 按数据源统计
    source_stats = {}
    for pkg in all_packages:
        subrepo = getattr(pkg, 'subrepo', 'unknown')
        source_stats[subrepo] = source_stats.get(subrepo, 0) + 1
    
    print("\n数据源统计:")
    for source, count in source_stats.items():
        print(f"  - {source}: {count} 个包")
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="仓库数据分析工具 - 支持OpenHarmony和Fedora",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python start.py openharmony              # 分析OpenHarmony仓库
  python start.py fedora                   # 分析Fedora 41仓库（默认）
  python start.py fedora --version 42      # 分析Fedora 42仓库
  python start.py fedora --version rawhide # 分析Fedora rawhide
  python start.py openharmony -o out/      # 指定输出目录
  python start.py --help                   # 显示帮助信息
        """
    )
    
    parser.add_argument(
        "system",
        choices=["openharmony", "fedora"],
        help="选择要分析的系统: openharmony 或 fedora"
    )
    
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出目录 (默认: generated/<system>)"
    )
    
    parser.add_argument(
        "-v", "--version",
        default="41",
        help="Fedora版本号 (例如: 41, 42, rawhide), 默认: 41"
    )
    parser.add_argument(
        "-r", "--release",
        default="stable",
        help="OpenHarmony发行通道 (例如: stable, beta, archived)，默认: stable"
    )
    
    args = parser.parse_args()
    
    # 确定输出目录
    if args.output:
        output_dir = args.output
    else:
        if args.system == "fedora":
            output_dir = f"generated/fedora_{args.version}"
        else:
            output_dir = f"generated/openharmony_{args.release}"
    
    # 根据参数选择分析系统
    if args.system == "openharmony":
        success = analyze_openharmony(output_dir, args.release)
    elif args.system == "fedora":
        success = analyze_fedora(output_dir, args.version)
    else:
        print(f"错误: 未知的系统类型 '{args.system}'")
        return 1
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

