# tasks/analysis.py
@app.task
def calculate_daily_stats():
    """计算每日统计"""
    repos = get_all_repositories()
    
    for repo in repos:
        stats = stats_calculator.calculate_repository_stats(repo.id)
        save_daily_stats(repo.id, stats)

@app.task
def update_outdated_status():
    """更新过期状态"""
    # 标记libyear > 0.5的包为过期
    mark_outdated_packages(threshold=0.5)