def build_clone_url(host, owner, repo, protocol='https'):
    """Build git clone URL."""
    # BUG: uses 'git' user for https protocol (only correct for SSH)
    if protocol == 'ssh':
        return f"git@{host}:{owner}/{repo}.git"
    else:
        # BUG: should be https://host/owner/repo.git
        return f"git@{host}:{owner}/{repo}.git"
