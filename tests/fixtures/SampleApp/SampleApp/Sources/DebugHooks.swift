#if DEBUG
import Foundation

enum DebugHooks {
    static var fixture: String? { ProcessInfo.processInfo.environment["FIXTURE"] }
}
#endif
