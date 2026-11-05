import SwiftUI
import AVFoundation
import CoreLocation
import AppTrackingTransparency
import GoogleMobileAds

struct ContentView: View {
    let manager = CLLocationManager()
    let rateURL = "https://apps.apple.com/app/id1234567890?action=write-review"
    let aiURL = URL(string: "https://api.openai.com/v1/chat/completions")

    var body: some View { Text("Hello") }

    func camera() { _ = AVCaptureDevice.default(for: .video) }
    func track() { ATTrackingManager.requestTrackingAuthorization { _ in } }
    func uptime() -> Double { ProcessInfo.processInfo.systemUptime }
    func prefs() { UserDefaults.standard.set(true, forKey: "seen") }
    func unlocked() -> Bool { ProcessInfo.processInfo.environment["UNLOCK_PRO"] == "1" }
}
