package com.team1.cyclingsafety

import android.os.Bundle
import android.os.CountDownTimer
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class EmergencyCountdownActivity : AppCompatActivity() {

    private var timer: CountDownTimer? = null
    private val totalSeconds = 15

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_emergency_countdown)

        val timerText = findViewById<TextView>(R.id.timerText)
        val cancelBtn = findViewById<Button>(R.id.btnCancel)

        cancelBtn.setOnClickListener {
            timer?.cancel()
            finish()
        }

        startCountdown(timerText)
    }

    private fun startCountdown(timerText: TextView) {
        timerText.text = totalSeconds.toString()

        timer = object : CountDownTimer(totalSeconds * 1000L, 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                timerText.text = (millisUntilFinished / 1000L).toInt().toString()
            }

            override fun onFinish() {
                EmergencyActions.openEmergencyDialer(this@EmergencyCountdownActivity)
                finish()
            }
        }.start()
    }

    override fun onDestroy() {
        timer?.cancel()
        super.onDestroy()
    }
}
