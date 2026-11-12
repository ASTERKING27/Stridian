package expo.modules.stridianhaptics

import android.content.Context
import android.media.AudioAttributes
import android.os.Build
import android.os.VibrationAttributes
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/*
 * The rich haptics of the design (code/haptics_data.py): launch, the tab sweep, level
 * reached, badges — patterns the system effects in expo-haptics can't make.
 *
 * `play(steps, budget, plain)`:
 *   steps   [primitive, at ms, scale, …] — a Composition (Android 11+), on phones whose
 *           motor plays every primitive in it;
 *   budget  [ms, amplitude 0–255, …] — the same moment as a waveform, for every other phone;
 *   plain   [off, on, off, on, …] ms — for a motor with no amplitude control (empty: the
 *           budget, any strength counting as on).
 * Both are played as touch feedback, so the phone's own touch-feedback setting and
 * strength apply. Resolves to what played: "rich", "budget" or "none".
 */
class StridianHapticsModule : Module() {
  private val context: Context
    get() = appContext.reactContext ?: throw Exceptions.ReactContextLost()
  private val vibrator: Vibrator
    get() = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
      (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager).defaultVibrator
    } else {
      @Suppress("DEPRECATION")
      context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
    }

  override fun definition() = ModuleDefinition {
    Name("StridianHaptics")

    AsyncFunction("play") { steps: List<Double>, budget: List<Double>, plain: List<Double> ->
      play(steps, budget, plain)
    }
  }

  private fun play(steps: List<Double>, budget: List<Double>, plain: List<Double>): String {
    val v = vibrator
    if (!v.hasVibrator()) return "none"
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && steps.size >= 3) {
      val ids = IntArray(steps.size / 3) { PRIMITIVES.getOrElse(steps[it * 3].toInt()) { PRIMITIVES[6] } }
      if (v.areAllPrimitivesSupported(*ids)) {
        // a primitive's delay counts from the end of the one before it
        val lengths = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) v.getPrimitiveDurations(*ids) else IntArray(ids.size)
        val composition = VibrationEffect.startComposition()
        var end = 0
        for (i in ids.indices) {
          val at = steps[i * 3 + 1].toInt()
          composition.addPrimitive(ids[i], steps[i * 3 + 2].toFloat().coerceIn(0f, 1f), maxOf(0, at - end))
          end = maxOf(at, end) + lengths[i]
        }
        vibrate(v, composition.compose())
        return "rich"
      }
    }
    if (budget.size < 2) return "none"
    val timings = LongArray(budget.size / 2) { budget[it * 2].toLong().coerceAtLeast(0L) }
    val amplitudes = IntArray(budget.size / 2) { budget[it * 2 + 1].toInt().coerceIn(0, 255) }
    val switched = if (plain.size >= 2) LongArray(plain.size) { plain[it].toLong().coerceAtLeast(0L) } else onOff(timings, amplitudes)
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
      @Suppress("DEPRECATION")
      v.vibrate(switched, -1)
      return "budget"
    }
    val effect = if (v.hasAmplitudeControl()) {
      VibrationEffect.createWaveform(timings, amplitudes, -1)
    } else {
      VibrationEffect.createWaveform(switched, -1)
    }
    vibrate(v, effect)
    return "budget"
  }

  private fun vibrate(v: Vibrator, effect: VibrationEffect) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
      v.vibrate(effect, VibrationAttributes.createForUsage(VibrationAttributes.USAGE_TOUCH))
    } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      @Suppress("DEPRECATION")
      v.vibrate(effect, AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
        .build())
    }
  }

  // Segments → the off, on, off, on… timings an on/off motor takes (it starts with an off).
  private fun onOff(timings: LongArray, amplitudes: IntArray): LongArray {
    val out = mutableListOf(0L)
    var on = false
    for (i in timings.indices) {
      val now = amplitudes[i] > 0
      if (now == on) out[out.size - 1] = out[out.size - 1] + timings[i] else { out.add(timings[i]); on = now }
    }
    return out.toLongArray()
  }

  companion object {
    // the order lib/haptics.js numbers them in
    private val PRIMITIVES = intArrayOf(
      VibrationEffect.Composition.PRIMITIVE_CLICK,
      VibrationEffect.Composition.PRIMITIVE_THUD,
      VibrationEffect.Composition.PRIMITIVE_SPIN,
      VibrationEffect.Composition.PRIMITIVE_QUICK_RISE,
      VibrationEffect.Composition.PRIMITIVE_SLOW_RISE,
      VibrationEffect.Composition.PRIMITIVE_QUICK_FALL,
      VibrationEffect.Composition.PRIMITIVE_TICK,
      VibrationEffect.Composition.PRIMITIVE_LOW_TICK
    )
  }
}
