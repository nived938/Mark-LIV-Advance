from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except Exception:  # QtWebEngine is optional at import time.
    QWebEngineView = None


class MapOverlay(QFrame):
    """Embedded map/browser overlay used by JarvisUI location views.

    The overlay owns its web view and exposes a single ``closed`` signal so the
    parent window can clear its reference when the user closes it. If QtWebEngine
    is unavailable, a clear in-app error is shown instead of crashing the HUD.
    """

    closed = pyqtSignal()

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setObjectName("mapOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        header = QFrame(self)
        header.setObjectName("mapOverlayHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 7, 8, 7)

        title = QLabel("LOCATION MAP", header)
        title.setObjectName("mapOverlayTitle")
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        close = QPushButton("CLOSE", header)
        close.setObjectName("mapOverlayClose")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setFixedHeight(28)
        close.clicked.connect(self.close)
        header_layout.addWidget(close)
        root.addWidget(header)

        if QWebEngineView is None:
            message = QLabel(
                "QtWebEngine is not available. Install PyQt6-WebEngine to display maps.",
                self,
            )
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            message.setWordWrap(True)
            root.addWidget(message, 1)
            self._web = None
        else:
            web = QWebEngineView(self)
            web.setObjectName("mapWebView")
            web.setUrl(QUrl(str(url)))
            root.addWidget(web, 1)
            self._web = web

        self.setStyleSheet(
            """
            #mapOverlay {
                background: #010d14;
                border: 1px solid #1a5c7a;
                border-radius: 8px;
            }
            #mapOverlayHeader {
                background: #010f18;
                border-bottom: 1px solid #0d3347;
            }
            #mapOverlayTitle {
                color: #8ffcff;
                font-family: 'Courier New';
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            #mapOverlayClose {
                color: #8ffcff;
                background: #001f2e;
                border: 1px solid #1a5c7a;
                border-radius: 4px;
                padding: 0 10px;
                font-family: 'Courier New';
                font-size: 9px;
                font-weight: 700;
            }
            #mapOverlayClose:hover {
                background: #0d3347;
            }
            """
        )

    def closeEvent(self, event):
        self.closed.emit()
        event.accept()
