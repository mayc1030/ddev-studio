"""
Vistas modulares de DDEV Studio.
"""

from ddev_studio.ui.views.details import ProjectDetailsView
from ddev_studio.ui.views.subsites import SubsitesManagerView
from ddev_studio.ui.views.drupal_tools import DrupalToolsView
from ddev_studio.ui.views.addons import AddonsMarketplaceView
from ddev_studio.ui.views.docker_monitor import DockerMonitorView
from ddev_studio.ui.views.tools import GlobalToolsView
from ddev_studio.ui.views.new_project import NewProjectView

__all__ = [
    "ProjectDetailsView",
    "SubsitesManagerView",
    "DrupalToolsView",
    "AddonsMarketplaceView",
    "DockerMonitorView",
    "GlobalToolsView",
    "NewProjectView",
]
