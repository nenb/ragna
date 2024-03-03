import panel as pn
import param

from ragna import __version__ as ragna_version

from .modal_configuration import ModalConfiguration

# negative as starting from most recent
NUMBER_OF_CHAT_BUTTONS = -5

CHAT_BUTTONS_STYLESHEET = """
:host {  
        width:90%;
        min-width: 200px;
}

:host div button {
overflow: hidden;
text-overflow: ellipsis;
text-align:left;
border: 0px !important;

}

:host div button:before {
content: url("/imgs/chat_bubble.svg");
margin-right: 10px;
display: inline-block;
}

:host(.selected) div button, :host div button:hover {
background-color: #F3F3F3 !important;
border-radius: 0px 5px 5px 0px !important;
border-left: solid 4px var(--accent-color) !important;
}
"""

HEADER_STYLESHEETS = """ 
:host { 
    background-color: #F9F9F9;
    border-bottom: 1px solid #EEEEEE;

    width: 100%;
    height: 54px;
    margin: 0;
}

:host div {
    display: flex;
    align-items: center;
    height: 100%;
}

:host img {
    margin: 5px;
    margin-left: 12px;
}

:host span { 
    margin-left: 20px;
    font-size: 24px;
    font-weight: 600;
}
"""

NEW_CHAT_BUTTON_STYLESHEETS = """ 
:host { 
    width: 90%;
    margin-left: 10px;
    margin-top: 10px;
}
:host div button { 
    background-color: var(--accent-color) !important;
    text-align: left;
}
"""

LEFT_SIDEBAR_STYLESHEETS = """   
:host { 
    overflow-x: hidden;
    height: 100%;
    width:100%;
    border-right: 1px solid #EEEEEE;
}
"""


class LeftSidebar(pn.viewable.Viewer):
    chat_names = param.List(default=None)
    current_chat_id = param.String(default=None)

    def __init__(
        self,
        api_wrapper,
        template,
        update_current_chat_callback,
        update_current_chat_metadata_callback,
    ):
        super().__init__()
        self.api_wrapper = api_wrapper

        self.template = template

        self.update_current_chat_callback = update_current_chat_callback

        self.update_current_chat_metadata_callback = (
            update_current_chat_metadata_callback
        )

        pn.state.onload(self.get_chat_names)

    async def get_chat_names(self):
        # Important: update chat_names BEFORE current_chat_id so chat_buttons called correctly
        chat_names = await self.api_wrapper.get_chat_names()
        if not chat_names:
            return
        self.current_chat_id = chat_names[0][0]
        self.chat_names = chat_names

    async def new_chat_ready_callback(self, new_chat_id):
        chat = await self.api_wrapper.get_chat(new_chat_id)

        self.chat_names = self.chat_names + [(new_chat_id, chat["metadata"]["name"])]

        # this will trigger the update of the central view
        self.update_current_chat_callback(
            chat["metadata"]["name"], chat["messages"], chat
        )

        # this will trigger the update of the right sidebar
        self.update_current_chat_metadata_callback(chat["metadata"])

        # this will trigger the update of the left sidebar itself
        self.current_chat_id = new_chat_id

        self.template.close_modal()

    def on_click_cancel_button(self, event):
        self.template.close_modal()

    def click_new_chat_callback(self, event):
        modal = ModalConfiguration(
            api_wrapper=self.api_wrapper,
            new_chat_ready_callback=self.new_chat_ready_callback,
            cancel_button_callback=self.on_click_cancel_button,
        )

        self.template.modal.objects[0].objects = [modal]
        self.template.open_modal()

    async def click_chat_name_callback(self, event):
        # This is a hack to avoid the event being triggered twice in a row
        if event.old > event.new:
            return

        chat_name = event.obj.name

        uuid = [uuid for uuid, name in self.chat_names if name == chat_name][0]

        chat = await self.api_wrapper.get_chat(uuid)

        # this will trigger the update of the central view
        self.update_current_chat_callback(
            {uuid: chat_name}, chat["messages"], chat["metadata"]
        )

        # this will trigger the update of the right sidebar
        self.update_current_chat_metadata_callback(chat["metadata"])

        # this will trigger the update of the left sidebar itself
        self.current_chat_id = uuid

    @pn.depends("chat_names", "current_chat_id")
    def chat_buttons(self):
        if not self.chat_names:
            return []
        else:
            buttons = []
            for uuid, name in self.chat_names[NUMBER_OF_CHAT_BUTTONS:]:
                button = pn.widgets.Button(
                    name=name,
                    button_style="outline",
                    stylesheets=[CHAT_BUTTONS_STYLESHEET],
                )
                button.on_click(self.click_chat_name_callback)

                if uuid == self.current_chat_id:
                    button.css_classes = ["selected"]
                buttons.append(button)

        return pn.FlexBox(*buttons)

    def header(self):
        return pn.pane.HTML(
            """<img src="imgs/ragna_logo.svg" height="32px" /><span>Ragna</span>""",
            stylesheets=[HEADER_STYLESHEETS],
        )

    def new_chat_button(self):
        new_chat_button = pn.widgets.Button(
            name="New Chat",
            button_type="primary",
            icon="plus",
            stylesheets=[NEW_CHAT_BUTTON_STYLESHEETS],
        )
        new_chat_button.on_click(self.click_new_chat_callback)
        return new_chat_button

    def __panel__(self):
        return pn.Column(
            self.header,
            self.new_chat_button,
            self.chat_buttons,
            pn.layout.VSpacer(),
            pn.pane.HTML(f"version: {ragna_version}"),
            stylesheets=[LEFT_SIDEBAR_STYLESHEETS],
        )
