# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from .default_maya_handler import DefaultMayaHandler

import maya.cmds


class ArnoldHandler(DefaultMayaHandler):
    """Render Handler for Arnold"""

    def __init__(self):
        """
        Initializes the Arnold Renderer and Arnold Renderer Handler
        """
        super().__init__()
        self.action_dict["error_on_arnold_license_fail"] = self.set_error_on_arnold_license_fail
        self.render_kwargs["batch"] = True

    def start_render(self, data: dict) -> None:
        """
        Starts a render.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['frame']

        Raises:
            RuntimeError: If no camera was specified and no renderable camera was found
        """
        frame = data.get("frame")
        if frame is None:
            raise RuntimeError("MayaClient: start_render called without a frame number.")
        self.render_kwargs["seq"] = frame

        self.render_kwargs["camera"] = self.get_camera_to_render(data)

        if "width" not in self.render_kwargs:
            self.render_kwargs["width"] = maya.cmds.getAttr("defaultResolution.width")
            print(
                f"No width was specified, defaulting to {self.render_kwargs['width']}",
                flush=True,
            )
        if "height" not in self.render_kwargs:
            self.render_kwargs["height"] = maya.cmds.getAttr("defaultResolution.height")
            print(
                f"No height was specified, defaulting to {self.render_kwargs['height']}",
                flush=True,
            )

        numXTiles = data.get("numXTiles")
        numYTiles = data.get("numYTiles")

        # Check if this is a tile rendering job (numXTiles and numYTiles are specified as job parameters)
        if (numXTiles is not None) and (numYTiles is not None):
            # Check that numXTiles and numYTiles are integers
            if (not isinstance(numXTiles, int)) or (not isinstance(numYTiles, int)):
                raise RuntimeError(
                    "numXTiles and numYTiles variables from run-data must be integers"
                )

            # Tile num uses 1 based indexing. First tile (top left) is x=1, y=1
            tileNumX = data.get("tileNumX")
            tileNumY = data.get("tileNumY")
            # Check that tileNumX and tileNumY are integers
            if (not isinstance(tileNumX, int)) or (not isinstance(tileNumY, int)):
                raise RuntimeError("tileNumX and tileNumY variables from run-data must be integers")

            deltaX, widthRemainder = divmod(self.render_kwargs["width"], numXTiles)
            deltaY, heightRemainder = divmod(self.render_kwargs["height"], numYTiles)

            # Calculate the border values for the tile
            # -1 from tilenums for minimums to get the end of the previous tile or 0. This is not done for max values as the max values need to reference the start of the next tile
            # -1 from max values because Maya uses inclusive ranges and 0 based indexing for coordinates
            # minX = left, maxX = right, minY = top, maxY = bottom
            minX = deltaX * (tileNumX - 1)
            maxX = (deltaX * tileNumX) - 1
            minY = deltaY * (tileNumY - 1)
            maxY = (deltaY * tileNumY) - 1

            # Add any remainder to the last row and column
            if tileNumX == numXTiles:
                maxX += widthRemainder
            if tileNumY == numYTiles:
                maxY += heightRemainder

            # Set the border ranges for the tile (left, right, top, bottom)
            maya.cmds.setAttr("defaultArnoldRenderOptions.regionMinX", minX)
            maya.cmds.setAttr("defaultArnoldRenderOptions.regionMaxX", maxX)
            maya.cmds.setAttr("defaultArnoldRenderOptions.regionMinY", minY)
            maya.cmds.setAttr("defaultArnoldRenderOptions.regionMaxY", maxY)
            print(f"minX={minX}, maxX={maxX}, minY={minY}, maxY={maxY}")

            prefix = data.get("output_file_prefix")

            # Set an ffmpeg glob pattern type compatible prefix for the tile (_tile_<y-coord>x<x_coord>_<numYtiles>x<numXtiles>_<prefix>) where x-coord and y-coord use 1-based indexing
            # This command takes inputs in sequential order and assembles them from left to right, top to down which is why the Y value needs to be first
            maya.cmds.setAttr(
                "defaultRenderGlobals.imageFilePrefix",
                f"_tile_{tileNumY}x{tileNumX}_{numYTiles}x{numXTiles}_{prefix}",
                type="string"
            )

            print(f'Output file name: {maya.cmds.getAttr("defaultRenderGlobals.imageFilePrefix")}')

        # Set the arnold render type so that we don't just make .ass files, but the actual image
        maya.cmds.setAttr("defaultArnoldRenderOptions.renderType", 0)

        # Set the log verbosity high enough that we get progress reporting output
        if maya.cmds.getAttr("defaultArnoldRenderOptions.log_verbosity") < 2:
            maya.cmds.setAttr("defaultArnoldRenderOptions.log_verbosity", 2)

        maya.cmds.arnoldRender(**self.render_kwargs)
        print(f"MayaClient: Finished Rendering Frame {frame}\n", flush=True)

    def set_error_on_arnold_license_fail(self, data: dict) -> None:
        """
        Sets the property that makes Maya fail if there is no Arnold License.
        If set to False the render will complete with a watermark.

        Args:
            data (dict): : The data given from the Adaptor. Keys expected:
                ['error_on_arnold_license_fail']
        """
        val = data.get("error_on_arnold_license_fail", True)
        maya.cmds.setAttr("defaultArnoldRenderOptions.abortOnLicenseFail", val)

    def set_render_layer(self, data: dict) -> None:
        """
        Sets the render layer.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['render_layer']

        Raises:
            RuntimeError: If the render layer cannot be found
        """
        render_layer_name = self.get_render_layer_to_render(data)
        if render_layer_name:
            maya.cmds.editRenderLayerGlobals(currentRenderLayer=render_layer_name)

    def set_image_height(self, data: dict) -> None:
        """
        Sets the image height.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_height']
        """
        yresolution = int(data.get("image_height", 0))
        if yresolution:
            self.render_kwargs["height"] = yresolution

    def set_image_width(self, data: dict) -> None:
        """
        Sets the image width.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['image_width']
        """
        xresolution = int(data.get("image_width", 0))
        if xresolution:
            self.render_kwargs["width"] = xresolution
