# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Defines the Render submitter command which is registered in Maya.
"""
import dataclasses
import json
import traceback
from typing import Optional

import maya.api.OpenMaya as om  # pylint: disable=import-error
import maya.cmds
from PySide2.QtWidgets import (  # pylint: disable=import-error; type: ignore
    QApplication,
)

from deadline.client.ui import gui_error_handler
from . import logger as deadline_logger  # type: ignore
from .data_classes.render_submitter_settings import (
    RenderSubmitterSettings,
    RenderSubmitterUISettings,
)
from .persistent_dataclass import PersistentDataclassError
from .maya_render_submitter import show_maya_render_submitter
from .job_bundle_output_test_runner import run_maya_render_submitter_job_bundle_output_test


class DeadlineCloudSubmitterCmd(om.MPxCommand):
    """
    Class used to create the DeadlineCloudSubmitter Mel Command.
    """

    @staticmethod
    def doIt(_):  # pylint: disable=invalid-name,
        """
        Open the Maya Integrated Submitter
        """

        # Build the GUI if we are in UI mode
        if om.MGlobal.mayaState() in [om.MGlobal.kInteractive, om.MGlobal.kBaseUIMode]:
            # Get the main Maya window so we can parent the submitter to it
            app = QApplication.instance()
            mainwin = [
                widget for widget in app.topLevelWidgets() if widget.objectName() == "MayaWindow"
            ][0]
            with gui_error_handler("Error opening the Deadline Cloud Submitter", mainwin):
                logger = deadline_logger()

                logger.info("Opening Amazon Deadline Cloud Submitter")
                scene_name = maya.cmds.file(query=True, sceneName=True)
                if not scene_name:
                    maya.cmds.confirmDialog(
                        title="Deadline Cloud Submitter",
                        message="The Maya Scene is not saved to disk. Please save it before opening the submitter dialog.",
                        button="OK",
                        defaultButton="OK",
                    )
                    return

                maybe_rs_settings: Optional[RenderSubmitterSettings] = None
                try:
                    maybe_rs_settings = RenderSubmitterSettings.load()
                except PersistentDataclassError:
                    traceback.print_exc()

                rs_settings: RenderSubmitterUISettings = RenderSubmitterUISettings()
                if maybe_rs_settings:
                    rs_settings.apply_saved_settings(maybe_rs_settings)

                # Since we're using Maya Python API 2.0, this return value will always be wrapped in a list
                # Consumers of this command will need to unpack the return value from this list
                om.MPxCommand.setResult(json.dumps(dataclasses.asdict(rs_settings)))

                show_maya_render_submitter(parent=mainwin, render_settings=rs_settings)


class DeadlineCloudJobBundleOutputTestsCmd(om.MPxCommand):
    """
    Class used to create the DeadlineCloudJobBundleOutputTests Mel Command.
    """

    @staticmethod
    def doIt(_):  # pylint: disable=invalid-name,
        """
        Runs a set of job bundle output tests from a directory.
        """
        run_maya_render_submitter_job_bundle_output_test()
