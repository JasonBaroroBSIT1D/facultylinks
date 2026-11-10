package edu.ustp.faculty_mobile

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.android.RenderMode

/**
 * TextureView avoids BLASTBufferQueue "Can't acquire next buffer" spam on some
 * MediaTek / Transsion devices when using the default SurfaceView + Impeller.
 */
class MainActivity : FlutterActivity() {
    override fun getRenderMode(): RenderMode = RenderMode.texture
}
