from PyQt6.QtCore import Qt, pyqtSlot, QObject
from PyQt6.QtWidgets import QDialog, QButtonGroup, QScrollArea, QWidget, QVBoxLayout, QDialogButtonBox, QSizePolicy, QRadioButton
from PyQt6.QtWebEngineCore import QWebEngineWebAuthUxRequest
from PyQt6.uic import loadUiType
from . import ui
from importlib import resources as rsrc

WebAuthDialogUi, baseClass = loadUiType(rsrc.files(ui) / "webauthdialog.ui")

class WebAuthUXDialog(baseClass):
    def __init__(self, parent, request : QWebEngineWebAuthUxRequest):
        super().__init__(parent)
        self.uxRequest = request
        self.ui = WebAuthDialogUi()
        self.ui.setupUi(self)
        self.buttonGroup = QButtonGroup(self)
        self.buttonGroup.setExclusive(True)
        self.scrollArea = QScrollArea(self)
        self.selectAccountWidget = QWidget(self)
        self.scrollArea.setWidget(self.selectAccountWidget)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.selectAccountWidget.resize(290, 150)
        self.selectAccountLayout = QVBoxLayout(self.selectAccountWidget)
        self.ui.m_mainVerticalLayout.addWidget(self.scrollArea)
        self.selectAccountLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.updateDisplay()
        self.ui.buttonBox.rejected.connect(self.onCancelRequest)
        self.ui.buttonBox.accepted.connect(self.onAcceptRequest)
        retry = self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Retry)
        retry.clicked.connect(self.onRetry)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)


    def updateDisplay(self):
        if self.uxRequest.state() == QWebEngineWebAuthUxRequest.WebAuthUxState.SelectAccount:
            self.setupSelectAccountUI()
        elif self.uxRequest.state() == QWebEngineWebAuthUxRequest.WebAuthUxState.CollectPin:
            self.setupCollectPinUI()
        elif self.uxRequest.state() == QWebEngineWebAuthUxRequest.WebAuthUxState.FinishTokenCollection:
            self.setupFinishCollectTokenUI()
        elif self.uxRequest.state() == QWebEngineWebAuthUxRequest.WebAuthUxState.RequestFailed:
            self.setupErrorUI()
        else:
            pass
        self.adjustSize()

    @pyqtSlot()
    def onCancelRequest(self):
        self.uxRequest.cancel()

    @pyqtSlot()
    def onAcceptRequest(self):
        if self.uxRequest.state() == QWebEngineWebAuthUxRequest.WebAuthUxState.SelectAccount:
            if self.buttonGroup.checkedButton():
                self.uxRequest.setSelectedAccount(self.buttonGroup.checkedButton().text())
        elif self.uxRequest.state() == QWebEngineWebAuthUxRequest.WebAuthUxState.CollectPin:
            self.uxRequest.setPin(self.ui.m_pinLineEdit.text())
        else:
            pass

    @pyqtSlot()
    def onRetry(self):
        self.uxRequest.retry()

    def setupSelectAccountUI(self):
        _tr = QObject.tr
        self.ui.m_headingLabel.setText(_tr("Choose a Passkey"))
        self.ui.m_description.setText(_tr("Which passkey do you want to use for ")
                                      + self.uxRequest.relyingPartyId() + _tr("? "))
        self.ui.m_pinGroupBox.setVisible(False)
        self.ui.m_mainVerticalLayout.removeWidget(self.ui.m_pinGroupBox)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(False)
        self.clearSelectAccountButtons()
        self.scrollArea.setVisible(True)
        self.selectAccountWidget.resize(self.width(), self.height())
        userNames = self.uxRequest.userNames()
        for name in iter(userNames):
            radioButton = QRadioButton(name)
            self.selectAccountLayout.addWidget(radioButton)
            self.buttonGroup.addButton(radioButton)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(_tr("Ok"))
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setVisible(True)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setVisible(True)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(False)

    def clearSelectAccountButtons(self):
        buttons = self.buttonGroup.buttons()
        for btn in iter(buttons):
            self.selectAccountLayout.removeWidget(btn)
            self.buttonGroup.removeButton(btn)

    def setupFinishCollectTokenUI(self):
        _tr = QObject.tr
        self.clearSelectAccountButtons()
        self.ui.m_headingLabel.setText(_tr("Use your security key with ") + self.uxRequest.relyingPartyId())
        self.ui.m_description.setText(_tr("Touch your security key again to complete the request."))
        self.ui.m_pinGroupBox.setVisible(False)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setVisible(False)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(False)
        self.scrollArea.setVisible(False)

    def setupCollectPinUI(self):
        _tr = QObject.tr
        self.clearSelectAccountButtons()
        self.ui.m_mainVerticalLayout.addWidget(self.ui.m_pinGroupBox)
        self.ui.m_pinGroupBox.setVisible(True)
        self.ui.m_confirmPinLabel.setVisible(False)
        self.ui.m_confirmPinLineEdit.setVisible(False)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(_tr("Next"))
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setVisible(True)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setVisible(True)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(False)
        self.scrollArea.setVisible(False)

        pinRequestInfo = self.uxRequest.pinRequest()
        if pinRequestInfo.reason == QWebEngineWebAuthUxRequest.PinEntryReason.Challenge:
            self.ui.m_headingLabel.setText(_tr("PIN Required"))
            self.ui.m_description.setText(_tr("Enter the PIN for your security key"))
            self.ui.m_confirmPinLabel.setVisible(False)
            self.ui.m_confirmPinLineEdit.setVisible(False)
        else:
            if pinRequestInfo.reason == QWebEngineWebAuthUxRequest.PinEntryReason.Set:
                self.ui.m_headingLabel.setText(_tr("New PIN Required"))
                self.ui.m_description.setText(_tr("Set new PIN for your security key"))
            else:
                self.ui.m_headingLabel.setText(_tr("Change PIN Required"))
                self.ui.m_description.setText(_tr("Change PIN for your security key"))
            self.ui.m_confirmPinLabel.setVisible(True)
            self.ui.m_confirmPinLineEdit.setVisible(True)

        errorDetails = ""
        if pinRequestInfo.error == QWebEngineWebAuthUxRequest.PinEntryError.InternalUvLocked:
            errorDetails = _tr("Internal User Verification Locked")
        elif pinRequestInfo.error == QWebEngineWebAuthUxRequest.PinEntryError.WrongPin:
            errorDetails = _tr("Wrong PIN")
        elif pinRequestInfo.error == QWebEngineWebAuthUxRequest.PinEntryError.TooShort:
            errorDetails = _tr("Too Short")
        elif pinRequestInfo.error == QWebEngineWebAuthUxRequest.PinEntryError.InvalidCharacters:
            errorDetails = _tr("Invalid Characters")
        elif pinRequestInfo.error == QWebEngineWebAuthUxRequest.PinEntryError.SameAsCurrentPin:
            errorDetails = _tr("Same as current PIN")

        if len(errorDetails) > 0:
            errorDetails += _tr(" ") + str(pinRequestInfo.remainingAttempts) + _tr(" attempts remaining")

        self.ui.m_pinEntryErrorLabel.setText(errorDetails)

    def setupErrorUI(self):
        _tr = QObject.tr
        self.clearSelectAccountButtons()
        errorDesc = ""
        errorHeading = _tr("Something went wrong")
        isVisibleRetry = False
        if self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.Timeout:
            errorDesc = _tr("Request Timeout")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.KeyNotRegistered:
            errorDesc = _tr("Key not registered")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.KeyAlreadyRegistered:
            errorDesc = _tr("You already registered this device. Try agin with device")
            isVisibleRetry = True
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.SoftPinBlock:
            errorDesc = _tr("The security key is locked because the wrong PIN was entered too many times. To unlock it, remove and reinsert it.")
            isVisibleRetry = True
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.HardPinBlock:
            errorDesc = _tr("The security key is locked because the wrong PIN was entered too many times. You'll need to reset the security key.")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.AuthenticatorRemovedDuringPinEntry:
            errorDesc = _tr("Authenticator removed during verification. Please reinsert and try again")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.AuthenticatorMissingResidentKeys:
            errorDesc = _tr("Authenticator doesn't have resident key support")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.AuthenticatorMissingLargeBlob:
            errorDesc = _tr("Authenticator missing Large Blob support")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.NoCommonAlgorithms:
            errorDesc = _tr("No common algorithms")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.StorageFull:
            errorDesc = _tr("Storage Full")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.UserConsentDenied:
            errorDesc = _tr("User consent denied")
        elif self.uxRequest.requestFailureReason() == QWebEngineWebAuthUxRequest.RequestFailureReason.WinUserCancelled:
            errorDesc = _tr("User Cancelled Request")

        self.ui.m_headingLabel.setText(errorHeading)
        self.ui.m_description.setText(errorDesc)
        self.ui.m_description.adjustSize()
        self.ui.m_pinGroupBox.setVisible(False)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setVisble(False)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(isVisibleRetry)
        if isVisibleRetry:
            self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setFocus()
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setVisible(True)
        self.ui.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(_tr("Close"))
        self.scrollArea.setVisible(False)