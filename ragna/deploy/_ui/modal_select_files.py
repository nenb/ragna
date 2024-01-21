import panel as pn
import param

from . import js
from . import styles as ui
from .components.file_selector import FileSelector


class ModalSelectFiles(pn.viewable.Viewer):
    cancel_button_callback = param.Callable()

    def __init__(self, api_wrapper, close_modal_callback, **params):
        super().__init__(**params)

        self.close_modal_callback = close_modal_callback

        self.api_wrapper = api_wrapper

        upload_endpoints = self.api_wrapper.upload_endpoints()

        self.file_selector = FileSelector(
            [],  # the allowed documents are set in the model_section function
            self.api_wrapper.auth_token,
            upload_endpoints["informations_endpoint"],
        )

        # Most widgets (including those that use from_param) should be placed after the super init call
        self.cancel_button = pn.widgets.Button(
            name="Cancel", button_type="default", min_width=375
        )
        self.cancel_button.on_click(close_modal_callback)

        self.upload_files_label = pn.pane.HTML()

        self.upload_files_button = pn.widgets.Button(
            name="Upload Files", button_type="primary", min_width=375
        )
        self.upload_files_button.on_click(self.did_click_on_upload_files_button)

    def did_click_on_upload_files_button(self, event):
        if len(self.file_selector.file_list) == 0:
            print("No file selected", self.file_selector.file_list)
            self.change_upload_files_label("missing_file")
        else:
            self.upload_files_button.disabled = True
            try:
                self.file_selector.perform_upload(event)
                self.upload_files_button.disabled = False
                self.close_modal_callback(event)
            except Exception:
                self.change_upload_files_label("upload_error")
                self.upload_files_button.disabled = False

    def change_upload_files_label(self, mode="normal"):
        if mode == "upload_error":
            self.upload_files_label.object = "<b>Upload files</b> (required)<span style='color:red;padding-left:100px;'><b>An error occured. Please try again or contact your administrator.</b></span>"
        elif mode == "missing_file":
            self.upload_files_label.object = (
                "<span style='color:red;'><b>Upload files</b> (required)</span>"
            )
        else:
            self.upload_files_label.object = "<b>Upload files</b> (required)"

    def __panel__(self):
        return pn.Column(
            pn.pane.HTML(
                f"""<h2>Select Files</h2>
                         Select local files to be used for local chats. <br />
                         <script>{js.reset_modal_size(ui.CONFIG_MODAL_WIDTH, ui.CONFIG_MODAL_MIN_HEIGHT)}</script>
                         """,
            ),
            ui.divider(),
            self.upload_files_label,
            self.file_selector,
            pn.Row(self.cancel_button, self.upload_files_button),
            min_height=ui.CONFIG_MODAL_MIN_HEIGHT,
            min_width=ui.CONFIG_MODAL_WIDTH,
            sizing_mode="stretch_both",
            height_policy="max",
        )
