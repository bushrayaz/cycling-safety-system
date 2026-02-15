package com.team1.cyclingsafety

import android.content.Context
import android.content.Intent
import android.net.Uri

object EmergencyActions {
    fun openEmergencyDialer(context: Context) {
        val intent = Intent(Intent.ACTION_DIAL).apply {
            data = Uri.parse("tel:911")
        }
        context.startActivity(intent)
    }
}
