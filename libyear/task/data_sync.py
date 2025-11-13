# tasks/data_sync.py
@app.task(bind=True, max_retries=3)
def full_sync_repository(self, repository_id):
    """全量同步仓库数据"""
    repo = get_repository(repository_id)
    sync_log = create_sync_log(repository_id, 'full', 'running')
    
    try:
        # 根据仓库类型调用不同的采集器
        if repo.type == 'rpm':
            packages = rpm_collector.sync_repository(repo.base_url)
        elif repo.type == 'deb':
            packages = deb_collector.sync_repository(repo.base_url)
        
        # 处理包数据
        processed = process_packages_data(packages, repository_id)
        
        # 更新同步日志
        update_sync_log(sync_log.id, 'success', {
            'packages_total': processed['total'],
            'packages_updated': processed['updated'], 
            'packages_added': processed['added'],
            'packages_removed': processed['removed']
        })
        
        # 更新仓库最后同步时间
        update_repository_sync_time(repository_id)
        
        return processed
        
    except Exception as e:
        update_sync_log(sync_log.id, 'failed', {'error_message': str(e)})
        self.retry(countdown=60 * 5)  # 5分钟后重试

@app.task
def incremental_sync_repository(repository_id):
    """增量同步仓库数据"""
    # 实现增量同步逻辑
    pass

@app.task  
def full_sync_all():
    """同步所有激活的仓库"""
    repos = get_active_repositories()
    for repo in repos:
        full_sync_repository.delay(repo.id)