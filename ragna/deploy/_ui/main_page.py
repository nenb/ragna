import panel as pn

from .central_view import CentralView
from .left_sidebar import LeftSidebar
from .right_sidebar import RightSidebar

MAIN_PAGE_STYLESHEETS = """   
:host { 
    background-color: rgb(248, 248, 248);
    height: 100%;
    width: 100%;
}

/* Enforces the width of the LeftSidebar 
which is the "first of type" with this class 
(first object in the row) */
.bk-panel-models-layout-Column:first-of-type {
    min-width: 220px;
    width: 15%;     
}
"""


class MainPage(pn.viewable.Viewer):
    def __init__(self, api_wrapper, template):
        super().__init__()

        self.api_wrapper = api_wrapper

        self.right_sidebar = RightSidebar()

        # central view coupled to right sidebar via chat info and source info buttons
        self.central_view = CentralView(
            api_wrapper=api_wrapper,
            click_chat_info_callback=self.right_sidebar.click_chat_info_callback,
            click_source_info_callback=self.right_sidebar.click_source_info_callback,
        )

        # left sidebar coupled to central view and right sidebar via chat selection button
        # left sidebar coupled to template (modal) via new chat button
        self.left_sidebar = LeftSidebar(
            api_wrapper=api_wrapper,
            template=template,
            update_current_chat_metadata_callback=self.right_sidebar.set_current_chat_metadata,
            update_current_chat_callback=self.central_view.update_current_chat_callback,
        )

    def __panel__(self):
        return pn.Row(
            self.left_sidebar,
            self.central_view,
            self.right_sidebar,
            stylesheets=[MAIN_PAGE_STYLESHEETS],
        )
