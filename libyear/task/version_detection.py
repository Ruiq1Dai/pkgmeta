# tasks/version_detection.py
@app.task
def detect_upstream_versions(package_ids):
    """检测上游版本信息"""
    packages = get_packages_by_ids(package_ids)
    
    for package in packages:
        try:
            upstream_info = version_detector.detect(
                package.package_name, 
                package.source_url
            )
            
            if upstream_info:
                update_package_upstream_info(
                    package.id,
                    upstream_info['version'],
                    upstream_info['release_date']
                )
                
        except Exception as e:
            logger.error(f"版本检测失败 {package.package_name}: {e}")