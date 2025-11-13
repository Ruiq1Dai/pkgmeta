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
from openharmony_parser import OHPMParser, OhpmIndexParser, OHPMJsonParser, GitCodeProjectsParser, GiteeRepoParser, build_openharmony_fedora_json, write_openharmony_fedora_primary_xml
from repodata_fetcher import RepodataFetcher
from repodata_parser import RepodataParser


def analyze_openharmony(output_dir: str = "generated", release: str = "stable"):
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
    # 使用临时目录存放中间文件，结束后清理
    tmp_dir = os.path.join(output_dir, ".tmp_openharmony")
    os.makedirs(tmp_dir, exist_ok=True)
    
    for source in sources:
        print(f"\n{'='*60}")
        print(f"处理数据源: {source['name']}")
        print(f"{'='*60}")
        
        # 步骤1: 获取数据
        print(f"\n1. 获取 {source['name']} 数据...")
        temp_file = os.path.join(tmp_dir, source['output'])
        
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

    # 步骤3: 依据 Fedora 契约写出最小产物（仅两个文件）
    print(f"\n{'='*60}")
    print("保存最小产物（契约对齐 Fedora）")
    print(f"{'='*60}")

    try:
        # 契约路径（以本文件位置为基准）
        here = Path(__file__).parent
        fedora_json_contract = here / 'generated' / 'fedora_41' / 'fedora_41_all_packages.json'
        fedora_xml_contract = here / 'generated' / 'fedora_41' / 'fedora_41_release_repodata.xml'

        # 生成 JSON（键顺序/空值策略/排序与 Fedora 对齐）
        json_items = build_openharmony_fedora_json(
            packages=all_packages,
            fedora_json_contract_path=str(fedora_json_contract),
            subrepo='release'
        )
        json_output = os.path.join(output_dir, 'openharmony_all_packages.json')
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(json_items, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON 输出: {json_output}")

        # 生成 XML（Fedora primary.xml 风格）
        xml_output = os.path.join(output_dir, 'openharmony_release_repodata.xml')
        write_openharmony_fedora_primary_xml(
            packages=all_packages,
            output_path=xml_output,
            fedora_xml_contract_path=str(fedora_xml_contract),
            subrepo='release'
        )
        print(f"✓ XML 输出: {xml_output}")
    except Exception as e:
        print(f"✗ 生成最小产物失败: {e}")
        return False

    # 清理中间文件，仅保留最终两个产物（位于 generated/ 根目录）
    try:
        if os.path.isdir(tmp_dir):
            for fname in os.listdir(tmp_dir):
                try:
                    os.remove(os.path.join(tmp_dir, fname))
                except Exception:
                    pass
            os.rmdir(tmp_dir)
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

