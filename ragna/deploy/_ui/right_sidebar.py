import panel as pn
import param

from . import styles as ui


class RightSidebar(pn.viewable.Viewer):
    content = param.List(default=[])
    current_chat_metadata = param.ClassSelector(class_=dict, default=None)

    def __init__(self, **params):
        super().__init__(**params)

        self.title = ""
        self.main_column = None

    def set_current_chat_metadata(self, chat_metadata):
        self.current_chat_metadata = chat_metadata

    def show(self):
        self.main_column.css_classes = ["visible_sidebar"]

    def hide(self, event):
        self.main_column.css_classes = ["hidden_sidebar"]

    def format_chat_metadata_markdown(self):
        pills = "".join(
            [
                f"""<div class='chat_document_pill'>{d['name']}</div>"""
                for d in self.current_chat_metadata["documents"]
            ]
        )

        formatted = "\n".join(
            [
                "To change configurations, start a new chat.\n",
                "**Uploaded Files**",
                f"<div class='pills_list'>{pills}</div><br />\n\n",
                "----",
                "**Source Storage**",
                f"""<span>{self.current_chat_metadata['source_storage']}</span>\n""",
                "----",
                "**Assistant**",
                f"""<span>{self.current_chat_metadata['assistant']}</span>\n""",
                "**Advanced configuration**",
                *[
                    f"- **{key.replace('_', ' ').title()}**: {value}"
                    for key, value in self.current_chat_metadata["params"].items()
                ],
            ]
        )

        return formatted

    @param.depends("current_chat_metadata", watch=True)
    def update_chat_info_content(self):
        markdown = self.format_chat_metadata_markdown()

        grid_height = len(self.current_chat_metadata["documents"]) // 3

        self.content = [
            pn.pane.Markdown(
                markdown,
                dedent=True,
                stylesheets=ui.stylesheets(
                    (":host", {"width": "100%"}),
                    (
                        ".pills_list",
                        {
                            # "background-color": "gold",
                            "display": "grid",
                            "grid-auto-flow": "row",
                            "row-gap": "10px",
                            "grid-template": f"repeat({grid_height}, 1fr) / repeat(3, 1fr)",
                            "max-height": "200px",
                            "overflow": "scroll",
                        },
                    ),
                    (
                        ".chat_document_pill",
                        {
                            "background-color": "rgb(241,241,241)",
                            "margin-left": "5px",
                            "margin-right": "5px",
                            "padding": "5px 15px",
                            "border-radius": "10px",
                            "color": "var(--accent-color)",
                            "width": "fit-content",
                            "grid-column": "span 1",
                        },
                    ),
                    ("ul", {"list-style-type": "none"}),
                ),
            ),
        ]

    def click_chat_info_callback(self):
        if not self.current_chat_metadata:
            return

        self.title = "Chat Info"

        self.update_chat_info_content()

        self.show()

    def update_source_info_content(self, sources):
        source_infos = []
        for rank, source in enumerate(sources, 1):
            location = source["location"]
            if location:
                location = f": page(s) {location}"

            if source["document"]["name"].endswith(".pdf"):
                if "," in source["location"]:
                    page_start = int(source["location"].split(",")[0])
                elif "-" in source["location"]:
                    page_start = int(source["location"].split("-")[0])
                else:
                    page_start = int(source["location"])
                # TODO: Build from source metadata
                html_link = f"dummy_link/my_pdf.pdf#page={page_start}"
                source_infos.append(
                    (
                        f"<b>{rank}. {source['document']['name']}</b> {location}",
                        pn.pane.HTML(
                            f"<a href={html_link} target='_blank'><b>{source['document']['name']}</b> {location}</a>",
                            css_classes=["source-content"],
                        ),
                    )
                )
            else:
                source_infos.append(
                    (
                        f"<b>{rank}. {source['document']['name']}</b> {location}",
                        pn.pane.Markdown(
                            source["content"], css_classes=["source-content"]
                        ),
                    )
                )

        self.content = [
            pn.pane.Markdown(
                "This response was generated using the following data from the uploaded files: <br />",
                dedent=True,
                stylesheets=[""" hr { width: 94%; height:1px;  }  """],
            ),
            pn.layout.Accordion(
                *source_infos,
                header_background="transparent",
                stylesheets=ui.stylesheets((":host", {"width": "100%"})),
            ),
        ]

    def click_source_info_callback(self, event, sources):
        self.title = "Source Info"

        self.update_source_info_content(sources)

        self.show()

    @pn.depends("content")
    def content_layout(self):
        return pn.Column(*self.content, stylesheets=[""" :host { width: 100%; } """])

    def header(self):
        return pn.pane.Markdown(
            f"## {self.title}",
            stylesheets=[
                """ :host { 
                            background-color: rgb(238, 238, 238);
                            margin:0;
                            padding-left:15px !important;
                            width:100%;
                    } """
            ],
        )

    def close_button(self):
        close_button = pn.widgets.Button(
            icon="x",
            button_type="light",
            css_classes=["close_button"],
            stylesheets=[
                """ 
                        :host {
                            position: absolute;
                            top: 6px;
                            right: 10px;
                            z-index: 99;
                        }
                        """
            ],
        )
        close_button.on_click(self.hide)

        return close_button

    def __panel__(self):
        self.main_column = pn.Column(
            self.close_button,
            self.header,
            self.content_layout,
            stylesheets=[
                """   
                                :host { 
                                        height:100%;
                                        min-width: unset;
                                        width: 0px;
                                        overflow:auto;

                                        margin-left: min(15px, 2%);
                                        border-left: 1px solid #EEEEEE;
                                }

                                .bk-panel-models-layout-Column {
                                    width: 100%;
                                }

                                :host .close_button {
                                    transform: translateX(20px);

                                }



                                :host(.visible_sidebar) {
                                        animation: 0.25s ease-in forwards show_right_sidebar;
                                        background-color: white;
                                }

                                @keyframes show_right_sidebar {
                                    from {
                                        min-width: unset;
                                        width: 0px;
                                    }

                                    to {
                                        min-width: 200px;
                                        width: 25%;
                                    }
                                }

                                
                                :host(.visible_sidebar) .close_button {
                                    animation: 0.25s ease-in forwards show_close_button;
                                }

                                @keyframes show_close_button {
                                    from {
                                        transform: translateX(20px);
                                    }
                                    to {
                                        transform: translateX(0px);
                                    }
                                }

                                /* hide */

                                :host(.hidden_sidebar) {
                                        animation: 0.33s ease-in forwards hide_right_sidebar;
                                }

                                @keyframes hide_right_sidebar {
                                    from {
                                        min-width: 200px;
                                        width: 25%;
                                    }

                                    to {
                                        min-width: unset;
                                        width: 0px;
                                    }
                                }

                                :host(.hidden_sidebar) .close_button {
                                    animation: 0.33s ease-in forwards hide_close_button;
                                }

                                @keyframes hide_close_button {
                                    from {
                                        transform: translateX(0px);
                                    }
                                    to {
                                        transform: translateX(20px);
                                    }
                                }

                                


                                """
            ],
        )

        return self.main_column
