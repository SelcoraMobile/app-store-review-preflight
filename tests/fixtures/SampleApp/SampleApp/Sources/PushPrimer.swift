import UIKit
import UserNotifications

/// Soft prompt shown before the system notification dialog.
final class PushPrimer {
    func show(from host: UIViewController) {
        let alert = UIAlertController(title: "Stay in the loop", message: "Get weekly updates.", preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Not now", style: .cancel))
        alert.addAction(UIAlertAction(title: "Allow", style: .default) { _ in
            UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
        })
        host.present(alert, animated: true)
    }
}
