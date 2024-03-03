from __future__ import annotations

from typing import Literal, cast

import panel as pn
import param
from panel.reactive import ReactiveHTML

from ragna._compat import anext

from . import styles as ui

# TODO : move all the CSS rules in a dedicated file

HEADER_STYLESHEETS = """
:host {  
    background-color: #F9F9F9;
    border-bottom: 1px solid #EEEEEE;
    width: 100% !important;
    margin:0px;
    height:54px;
    overflow:hidden;
}

:host div {
    vertical-align: middle;
}
"""

HEADER_CHAT_NAME_STYLESHEETS = """ 
:host p {
    max-width: 50%;
    height:100%;

    text-overflow: ellipsis;
    white-space: nowrap;
    overflow: hidden;
    margin: 0px 0px 0px 10px;

    font-size:20px;
    text-decoration: underline;
    text-underline-offset: 4px;

    /* I don't understand why this is necessary to vertically align the text ... */
    line-height:250%; 
    
}
"""

CENTRAL_VIEW_STYLESHEETS = """                    
:host { 
    background-color: #F9F9F9;
    height:100%;
    max-width: 100%;
    margin-left: min(15px, 2%);
    border-left: 1px solid #EEEEEE;
    border-right: 1px solid #EEEEEE;
}
"""

message_stylesheets = [
    """ 
            :host .right, :host .center {
                    width:100% !important;
            }
    """,
    """ 
            :host .left {
                height: unset !important;
                min-height: unset !important;
            }
    """,
    """
            :host div.bk-panel-models-layout-Column:not(.left) { 
                    width:100% !important;
            }
    """,
    """
            :host .message {
                width: calc(100% - 15px);
                box-shadow: unset;
                font-size: unset;
                background-color: unset;
            }
    """,
    """
            :host .avatar {
                margin-top:0px;
                box-shadow: unset;
            }
    """,
]


class CopyToClipboardButton(ReactiveHTML):
    title = param.String(default=None, doc="The title of the button ")
    value = param.String(default=None, doc="The text to copy to the clipboard.")

    _template = """
        <div type="button" 
                id="copy-button"
                onclick="${script('copy_to_clipboard')}"
                class="container"
                style="cursor: pointer;"
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-clipboard" width="16" height="16" 
                    viewBox="0 0 24 24" stroke-width="2" stroke="gray" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M9 5h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2h-2" />
                <path d="M9 3m0 2a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v0a2 2 0 0 1 -2 2h-2a2 2 0 0 1 -2 -2z" />
            </svg>
            <span>${title}</span>
        </div>            
        """

    _scripts = {
        "copy_to_clipboard": """navigator.clipboard.writeText(`${data.value}`);"""
    }

    _stylesheets = [
        """ div.container { 
                            
                            display:flex;
                            flex-direction: row;
                            margin: 7px 10px;
                    
                            color:gray;
                        } 
                    
                        svg {
                            margin-right:5px;
                        }

                    """
    ]


class RagnaMessage:
    def __init__(self) -> None:
        self.content_pane = None

    def create_msg(
        self,
        content,
        role,
        user,
        sources,
        timestamp,
        on_click_source_info_callback,
        show_timestamp,
    ):
        css_class = f"message-content-{role}"

        self.content_pane = pn.pane.Markdown(
            content,
            css_classes=["message-content", css_class],
            stylesheets=ui.stylesheets(
                (
                    "table",
                    {"margin-top": "10px", "margin-bottom": "10px"},
                )
            ),
        )

        def _copy_and_source_view_buttons() -> pn.Row:
            return pn.Row(
                CopyToClipboardButton(
                    value=self.content_pane.object,
                    title="Copy",
                    stylesheets=[
                        ui.CHAT_INTERFACE_CUSTOM_BUTTON,
                    ],
                ),
                pn.widgets.Button(
                    name="Source Info",
                    icon="info-circle",
                    stylesheets=[
                        ui.CHAT_INTERFACE_CUSTOM_BUTTON,
                    ],
                    on_click=lambda event: on_click_source_info_callback(
                        event, sources
                    ),
                ),
            )

        if role == "assistant":
            assert sources is not None
            css_class = "message-content-assistant-with-buttons"
            object = pn.Column(
                self.content_pane,
                _copy_and_source_view_buttons(),
                css_classes=[css_class],
            )
        else:
            object = self.content_pane

        object.stylesheets.extend(
            ui.stylesheets(
                (
                    f":host(.{css_class})",
                    (
                        {"background-color": "rgb(243, 243, 243) !important"}
                        if role == "user"
                        else {
                            "background-color": "none",
                            "border": "rgb(234, 234, 234)",
                            "border-style": "solid",
                            "border-width": "1.2px",
                            "border-radius": "5px",
                        }
                    ),
                )
            ),
        )

        def _avatar_lookup(user: str) -> str:
            if role == "system":
                return "imgs/ragna_logo.svg"
            elif role == "user":
                return "👤"

            try:
                organization, model = user.split("/")
            except ValueError:
                organization = ""
                model = user

            if organization == "Ragna":
                return "imgs/ragna_logo.svg"
            elif organization == "OpenAI":
                if model.startswith("gpt-3"):
                    return "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/1024px-ChatGPT_logo.svg.png?20230318122128"
                elif model.startswith("gpt-4"):
                    return (
                        "https://upload.wikimedia.org/wikipedia/commons/a/a4/GPT-4.png"
                    )
            elif organization == "Anthropic":
                return (
                    "https://upload.wikimedia.org/wikipedia/commons/1/14/Anthropic.png"
                )

            return model[0].upper()

        c = pn.chat.ChatMessage(
            object=object,
            user=user,
            timestamp=timestamp,
            show_timestamp=show_timestamp,
            show_reaction_icons=False,
            show_user=False,
            show_copy_icon=False,
            css_classes=[f"message-{role}"],
            avatar_lookup=_avatar_lookup,
        )

        if message_stylesheets not in c._stylesheets:
            c._stylesheets = c._stylesheets + message_stylesheets

        return c


class RagnaChatInterface(pn.chat.ChatInterface):
    get_user_from_role = param.Callable(allow_None=True)

    @param.depends("placeholder_text", watch=True, on_init=True)
    def _update_placeholder(self):
        self._placeholder = RagnaMessage().create_msg(
            ui.message_loading_indicator,
            role="system",
            user=self.get_user_from_role("system"),
            show_timestamp=False,
            sources=None,
            timestamp=None,
            on_click_source_info_callback=None,
        )

    def _build_message(self, *args, **kwargs) -> pn.chat.ChatMessage | None:
        message = super()._build_message(*args, **kwargs)
        if message is None:
            return None

        # We only ever hit this function for user inputs, since we control the
        # generation of the system and assistant messages manually. Thus, we can
        # unconditionally create a user message here.
        return RagnaMessage().create_msg(
            message.object,
            role="user",
            user=self.user,
            sources=None,
            timestamp=None,
            on_click_source_info_callback=None,
            show_timestamp=True,
        )


class CentralView(pn.viewable.Viewer):
    current_chat_metadata = param.ClassSelector(class_=dict, default=None)
    current_chat_name_mapping = param.ClassSelector(class_=dict, default=None)
    current_chat_messages = param.List(default=[])

    def __init__(
        self, api_wrapper, click_chat_info_callback, click_source_info_callback
    ):
        super().__init__()

        # FIXME: make this dynamic from the login
        self.user = ""
        self.api_wrapper = api_wrapper
        self.chat_info_button = pn.widgets.Button(
            name="Information",
            on_click=lambda event: click_chat_info_callback(),
            button_style="outline",
            icon="info-circle",
            stylesheets=[":host { margin-top:10px; }"],
        )
        self.click_source_info_callback = click_source_info_callback
        self.toggle_loading_state = None

    def get_user_from_role(self, role: Literal["system", "user", "assistant"]) -> str:
        if role == "system":
            return "Ragna"
        elif role == "user":
            return cast(str, self.user)
        elif role == "assistant":
            return cast(str, self.current_chat_metadata["assistant"])
        else:
            raise RuntimeError

    async def chat_callback(
        self, content: str, user: str, instance: pn.chat.ChatInterface
    ):
        try:
            uuid = list(self.current_chat_name_mapping.keys())[0]
            answer_stream = self.api_wrapper.answer(uuid, content)
            answer = await anext(answer_stream)

            ragna_message = RagnaMessage()

            message = ragna_message.create_msg(
                answer["content"],
                role="assistant",
                user=self.get_user_from_role("assistant"),
                sources=answer["sources"],
                timestamp=None,
                on_click_source_info_callback=self.click_source_info_callback,
                show_timestamp=True,
            )
            yield message

            async for chunk in answer_stream:
                ragna_message.content_pane.object += chunk["content"]

        except Exception:
            yield RagnaMessage().create_msg(
                (
                    "Sorry, something went wrong. "
                    "If this problem persists, please contact your administrator."
                ),
                role="system",
                user=self.get_user_from_role("system"),
                sources=None,
                timestamp=None,
                on_click_source_info_callback=self.click_source_info_callback,
                show_timestamp=True,
            )

    @pn.depends("current_chat_messages")
    def chat_interface(self):
        if self.current_chat_messages is None:
            return

        messages = [
            RagnaMessage().create_msg(
                message["content"],
                message["role"],
                self.get_user_from_role(message["role"]),
                message["sources"],
                message["timestamp"],
                self.click_source_info_callback,
                show_timestamp=True,
            )
            for message in self.current_chat_messages
        ]

        return RagnaChatInterface(
            *messages,
            callback=self.chat_callback,
            user=self.user,
            get_user_from_role=self.get_user_from_role,
            show_rerun=False,
            show_undo=False,
            show_clear=False,
            show_button_name=False,
            view_latest=True,
            sizing_mode="stretch_width",
            # TODO: Remove the parameter when
            #  https://github.com/holoviz/panel/issues/6115 is merged and released. We
            #  currently need it to avoid sending a message when the text input is
            #  de-focussed. But this also means we can't hit enter to send.
            auto_send_types=[],
            widgets=[
                pn.widgets.TextInput(
                    placeholder="Ask a question about the documents",
                    stylesheets=ui.stylesheets(
                        (
                            ":host input[type='text']",
                            {
                                "border": "none !important",
                                "box-shadow": "0px 0px 6px 0px rgba(0, 0, 0, 0.2)",
                                "padding": "10px 10px 10px 15px",
                            },
                        ),
                        (
                            ":host input[type='text']:focus",
                            {
                                "box-shadow": "0px 0px 8px 0px rgba(0, 0, 0, 0.3)",
                            },
                        ),
                    ),
                )
            ],
            card_params=dict(
                stylesheets=ui.stylesheets(
                    (":host", {"border": "none !important"}),
                    (
                        ".chat-feed-log",
                        {
                            "padding-right": "18%",
                            "margin-left": "18%",
                            "padding-top": "25px !important",
                        },
                    ),
                    (
                        ".chat-interface-input-container",
                        {
                            "margin-left": "19%",
                            "margin-right": "20%",
                            "margin-bottom": "20px",
                        },
                    ),
                )
            ),
            show_activity_dot=False,
        )

    @pn.depends("current_chat_name_mapping")
    def header(self):
        if self.current_chat_name_mapping is None:
            return

        current_chat_name = list(self.current_chat_name_mapping.values())[0]

        chat_name_header = pn.pane.HTML(
            f"<p>{current_chat_name}</p>",
            sizing_mode="stretch_width",
            stylesheets=[HEADER_CHAT_NAME_STYLESHEETS],
        )

        return pn.Row(
            chat_name_header,
            self.chat_info_button,
            stylesheets=[HEADER_STYLESHEETS],
        )

    def update_current_chat_callback(
        self, chat_name_mapping, chat_messages, chat_metadata
    ):
        self.toggle_loading_state(True)
        self.current_chat_name_mapping = chat_name_mapping
        self.current_chat_metadata = chat_metadata
        self.current_chat_messages = chat_messages
        self.toggle_loading_state(False)

    def __panel__(self):
        col = pn.Column(
            self.header,
            self.chat_interface,
            sizing_mode="stretch_width",
            stylesheets=[CENTRAL_VIEW_STYLESHEETS],
        )

        def _toggle_loading_state(state):
            col.loading = state

        self.toggle_loading_state = _toggle_loading_state

        return col
