# tasks/libyear_calculation.py
@app.task
def calculate_libyear_for_package(package_id):
    """计算单个包的libyear"""
    package = get_package(package_id)
    
    if package.upstream_release_date and package.system_release_date:
        libyear = libyear_calculator.calculate(
            package.system_release_date,
            package.upstream_release_date
        )
        
        update_package_libyear(package.id, libyear)

@app.task
def recalculate_all_libyears():
    """重新计算所有包的libyear"""
    packages = get_all_packages_with_dates()
    for package in packages:
        calculate_libyear_for_package.delay(package.id)