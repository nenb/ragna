import panel as pn
import param


class FileSelector(pn.viewable.Viewer):
    allowed_documents = param.List(default=[])
    allowed_documents_str = param.String(default="")

    file_list = param.List(default=[])

    title = param.String(default="")

    def __init__(self, allowed_documents, token, informations_endpoint, **params):
        super().__init__(**params)

        self.token = token
        self.informations_endpoint = informations_endpoint

        self.file_selector_widget = pn.widgets.FileSelector()
        self.file_selector_widget.link(self, value="file_list")

    @param.depends("allowed_documents", watch=True)
    def update_allowed_documents_str(self):
        if len(self.allowed_documents) == 1:
            self.allowed_documents_str = (
                "Only " + self.allowed_documents[0] + " files are allowed."
            )
        else:
            self.allowed_documents_str = "Allowed files : " + ", ".join(
                self.allowed_documents
            )

    def perform_upload(self, event=None):
        self.loading = True
        print("Need to implement backend logic to deal with file name selection")
        print("Need to implement error logic to prevent upload of invalid file formats")
        self.loading = False

    def __panel__(self):
        return pn.Row(self.file_selector_widget)
