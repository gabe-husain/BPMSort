// BPM Player: a tiny floating, borderless, always-on-top Mac widget of the /player page.
// Fully native (no Python, no WebKit). Talks to Spotify directly using PKCE, so no client secret.
// Build with widget/build.sh
import Cocoa
import CryptoKit
import Network
import Security

let port: UInt16 = 47823 // only used for the login redirect, out of the way of dev servers
let redirectURI = "http://127.0.0.1:\(port)/callback"
let defaultSize = NSSize(width: 220, height: 220)

//
//       PREFERENCES
//

enum Prefs {
    static let defaults = UserDefaults.standard
    static let changed = Notification.Name("PrefsChanged")

    static var speedAuto: Bool {
        get { defaults.object(forKey: "speedAuto") as? Bool ?? true }
        set { defaults.set(newValue, forKey: "speedAuto") }
    }
    // points per second
    static var speed: Double {
        get { defaults.object(forKey: "speed") as? Double ?? 10 }
        set { defaults.set(newValue, forKey: "speed") }
    }
    static var sizeAuto: Bool {
        get { defaults.object(forKey: "sizeAuto") as? Bool ?? true }
        set { defaults.set(newValue, forKey: "sizeAuto") }
    }
    // points
    static var size: Double {
        get { defaults.object(forKey: "size") as? Double ?? 13 }
        set { defaults.set(newValue, forKey: "size") }
    }
}

enum Keychain {
    static let service = "com.gabehusain.bpmsort.player"

    static func query(_ key: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: key]
    }

    static func get(_ key: String) -> String? {
        var q = query(key)
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: AnyObject?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let data = out as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func set(_ key: String, _ value: String?) {
        SecItemDelete(query(key) as CFDictionary)
        guard let value else { return }
        var q = query(key)
        q[kSecValueData as String] = Data(value.utf8)
        SecItemAdd(q as CFDictionary, nil)
    }
}

//
//       SPOTIFY
//

struct Track: Equatable {
    let id: String
    let title: String
    let artist: String
    let imageURL: URL?
    let remaining: TimeInterval
}

enum Playback {
    case playing(Track)
    case nothing
    case loggedOut
    case failed(retryAfter: TimeInterval)
}

final class Spotify {
    let clientID: String
    var onLogin: (() -> Void)?

    private var accessToken: String?
    private var expiresAt = Date.distantPast
    private var listener: NWListener?
    private var verifier = ""
    private var state = ""

    private lazy var cachedRefresh: String? = Keychain.get("refresh_token")
    private var refreshToken: String? {
        get { cachedRefresh }
        set { cachedRefresh = newValue; Keychain.set("refresh_token", newValue) }
    }

    var isLoggedIn: Bool { refreshToken != nil }

    init(clientID: String) {
        self.clientID = clientID
    }

    func logout() {
        accessToken = nil
        refreshToken = nil
    }

    // Opens Spotify's login in the browser, the redirect comes back to a one-shot local listener
    func login() {
        verifier = randomString(64)
        state = randomString(16)
        let challenge = base64URL(Data(SHA256.hash(data: Data(verifier.utf8))))

        startListener()
        var url = URLComponents(string: "https://accounts.spotify.com/authorize")!
        url.queryItems = [
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "client_id", value: clientID),
            URLQueryItem(name: "redirect_uri", value: redirectURI),
            URLQueryItem(name: "scope", value: "user-read-currently-playing"),
            URLQueryItem(name: "state", value: state),
            URLQueryItem(name: "code_challenge_method", value: "S256"),
            URLQueryItem(name: "code_challenge", value: challenge),
        ]
        NSWorkspace.shared.open(url.url!)
    }

    func currentlyPlaying(retried: Bool = false, done: @escaping (Playback) -> Void) {
        validToken { token in
            guard let token else { return done(self.isLoggedIn ? .failed(retryAfter: 10) : .loggedOut) }

            var request = URLRequest(url: URL(string: "https://api.spotify.com/v1/me/player/currently-playing?additional_types=track,episode")!)
            request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
            request.timeoutInterval = 10
            URLSession.shared.dataTask(with: request) { data, response, _ in
                let status = (response as? HTTPURLResponse)?.statusCode ?? 0
                let retryAfter = Double((response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Retry-After") ?? "") ?? 10
                DispatchQueue.main.async {
                    switch status {
                    case 200:
                        done(Spotify.parse(data) ?? .nothing)
                    case 204:
                        done(.nothing)
                    case 401 where !retried:
                        self.accessToken = nil
                        self.currentlyPlaying(retried: true, done: done)
                    default:
                        done(.failed(retryAfter: retryAfter))
                    }
                }
            }.resume()
        }
    }

    private static func parse(_ data: Data?) -> Playback? {
        guard let data,
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let item = json["item"] as? [String: Any],
              let id = item["id"] as? String else { return nil }

        // tracks have an album and artists, podcast episodes have a show
        let album = item["album"] as? [String: Any] ?? item["show"] as? [String: Any]
        let artists = (item["artists"] as? [[String: Any]])?.compactMap { $0["name"] as? String }
        let artist = artists?.first ?? (item["show"] as? [String: Any])?["name"] as? String ?? ""

        // pick the image closest to 300px, big enough for any widget size
        let images = album?["images"] as? [[String: Any]] ?? item["images"] as? [[String: Any]] ?? []
        let image = images.min { abs(($0["width"] as? Int ?? 0) - 300) < abs(($1["width"] as? Int ?? 0) - 300) }

        let duration = item["duration_ms"] as? Double ?? 0
        let progress = json["progress_ms"] as? Double ?? 0
        return .playing(Track(
            id: id,
            title: item["name"] as? String ?? "",
            artist: artist,
            imageURL: (image?["url"] as? String).flatMap(URL.init(string:)),
            remaining: max(0, duration - progress) / 1000))
    }

    private func validToken(_ done: @escaping (String?) -> Void) {
        if let accessToken, Date() < expiresAt { return done(accessToken) }
        guard let refreshToken else { return done(nil) }
        requestToken(["grant_type": "refresh_token", "refresh_token": refreshToken, "client_id": clientID]) { [weak self] ok in
            done(ok ? self?.accessToken : nil)
        }
    }

    private func requestToken(_ form: [String: String], done: @escaping (Bool) -> Void) {
        var request = URLRequest(url: URL(string: "https://accounts.spotify.com/api/token")!)
        request.httpMethod = "POST"
        request.timeoutInterval = 10
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        var body = URLComponents()
        body.queryItems = form.map { URLQueryItem(name: $0.key, value: $0.value) }
        request.httpBody = body.percentEncodedQuery?.replacingOccurrences(of: "+", with: "%2B").data(using: .utf8)

        URLSession.shared.dataTask(with: request) { data, response, _ in
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            let json = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
            DispatchQueue.main.async {
                guard status == 200, let json, let token = json["access_token"] as? String else {
                    // a rejected refresh token means we have to log in again
                    if status == 400 { self.logout() }
                    return done(false)
                }
                self.accessToken = token
                self.expiresAt = Date().addingTimeInterval((json["expires_in"] as? Double ?? 3600) - 60)
                // Spotify can rotate the refresh token, keep the old one otherwise
                if let refresh = json["refresh_token"] as? String { self.refreshToken = refresh }
                done(true)
            }
        }.resume()
    }

    //
    //       LOGIN REDIRECT LISTENER
    //

    private func startListener() {
        listener?.cancel()
        let params = NWParameters.tcp
        params.allowLocalEndpointReuse = true
        params.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: NWEndpoint.Port(rawValue: port)!)
        guard let listener = try? NWListener(using: params) else { return }
        listener.newConnectionHandler = { [weak self] connection in self?.handle(connection) }
        listener.start(queue: .main)
        self.listener = listener
    }

    private func stopListener() {
        listener?.cancel()
        listener = nil
    }

    private func handle(_ connection: NWConnection) {
        connection.start(queue: .main)
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16384) { [weak self] data, _, _, _ in
            guard let self,
                  let data, let request = String(data: data, encoding: .utf8),
                  let line = request.components(separatedBy: "\r\n").first else { return connection.cancel() }

            let target = line.split(separator: " ").dropFirst().first.map(String.init) ?? "/"
            let url = URLComponents(string: "http://127.0.0.1" + target)
            guard url?.path == "/callback" else { return self.respond(connection, 404, "Not found") }

            let query = Dictionary((url?.queryItems ?? []).map { ($0.name, $0.value ?? "") }, uniquingKeysWith: { first, _ in first })
            // state must match the one made at login, otherwise this could be a forged request
            guard !self.state.isEmpty, query["state"] == self.state else {
                return self.respond(connection, 400, "State mismatch, try logging in again.")
            }
            self.stopListener()
            guard let code = query["code"] else { return self.respond(connection, 400, "Login cancelled.") }

            self.respond(connection, 200, "Logged in to BPM Player, you can close this tab.")
            self.requestToken([
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirectURI,
                "client_id": self.clientID,
                "code_verifier": self.verifier,
            ]) { ok in if ok { self.onLogin?() } }
        }
    }

    private func respond(_ connection: NWConnection, _ status: Int, _ message: String) {
        let body = "<body style=\"font:15px -apple-system;padding:40px\">\(message)</body>"
        let response = "HTTP/1.1 \(status) OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: \(body.utf8.count)\r\nConnection: close\r\n\r\n" + body
        connection.send(content: Data(response.utf8), completion: .contentProcessed { _ in connection.cancel() })
    }

    private func randomString(_ bytes: Int) -> String {
        var data = Data(count: bytes)
        _ = data.withUnsafeMutableBytes { SecRandomCopyBytes(kSecRandomDefault, bytes, $0.baseAddress!) }
        return base64URL(data)
    }

    private func base64URL(_ data: Data) -> String {
        data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

//
//       COLORS (same math as get_dominant_color / colorsys in routes.py)
//

typealias RGB = (r: Double, g: Double, b: Double)

func dominantColor(_ image: CGImage, k: Int = 2) -> RGB {
    let side = 100
    guard let ctx = CGContext(data: nil, width: side, height: side, bitsPerComponent: 8, bytesPerRow: side * 4,
                              space: CGColorSpace(name: CGColorSpace.sRGB)!,
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return (0, 0, 0) }
    ctx.interpolationQuality = .medium
    ctx.draw(image, in: CGRect(x: 0, y: 0, width: side, height: side))
    guard let raw = ctx.data else { return (0, 0, 0) }
    let bytes = raw.bindMemory(to: UInt8.self, capacity: side * side * 4)
    let pixels = (0..<side * side).map { SIMD3<Double>(Double(bytes[$0 * 4]), Double(bytes[$0 * 4 + 1]), Double(bytes[$0 * 4 + 2])) }

    // simple k-means, seeded with the first pixel and the pixel furthest from it
    func distance(_ a: SIMD3<Double>, _ b: SIMD3<Double>) -> Double { ((a - b) * (a - b)).sum() }
    var centroids = [pixels[0]]
    while centroids.count < k {
        let seeds = centroids
        func gap(_ p: SIMD3<Double>) -> Double { seeds.map { distance(p, $0) }.min()! }
        centroids.append(pixels.max { gap($0) < gap($1) }!)
    }

    var counts = [Int](repeating: 0, count: k)
    for _ in 0..<20 {
        var sums = [SIMD3<Double>](repeating: .zero, count: k)
        counts = [Int](repeating: 0, count: k)
        for pixel in pixels {
            let nearest = (0..<k).min { distance(pixel, centroids[$0]) < distance(pixel, centroids[$1]) }!
            sums[nearest] += pixel
            counts[nearest] += 1
        }
        let updated = (0..<k).map { counts[$0] > 0 ? (sums[$0] / Double(counts[$0])).rounded(.down) : centroids[$0] }
        if updated == centroids { break }
        centroids = updated
    }

    // centroid of the largest cluster
    let largest = centroids[counts.indices.max { counts[$0] < counts[$1] }!]
    return (largest.x, largest.y, largest.z)
}

func rgbToHLS(_ c: RGB) -> (h: Double, l: Double, s: Double) {
    let maxc = max(c.r, c.g, c.b), minc = min(c.r, c.g, c.b)
    let l = (minc + maxc) / 2
    if minc == maxc { return (0, l, 0) }
    let s = l <= 0.5 ? (maxc - minc) / (maxc + minc) : (maxc - minc) / (2 - maxc - minc)
    let rc = (maxc - c.r) / (maxc - minc), gc = (maxc - c.g) / (maxc - minc), bc = (maxc - c.b) / (maxc - minc)
    var h = c.r == maxc ? bc - gc : c.g == maxc ? 2 + rc - bc : 4 + gc - rc
    h = (h / 6).truncatingRemainder(dividingBy: 1)
    return (h < 0 ? h + 1 : h, l, s)
}

func hlsToRGB(_ h: Double, _ l: Double, _ s: Double) -> RGB {
    if s == 0 { return (l, l, l) }
    let m2 = l <= 0.5 ? l * (1 + s) : l + s - l * s
    let m1 = 2 * l - m2
    func v(_ hue: Double) -> Double {
        let hue = hue - floor(hue)
        if hue < 1 / 6 { return m1 + (m2 - m1) * hue * 6 }
        if hue < 0.5 { return m2 }
        if hue < 2 / 3 { return m1 + (m2 - m1) * (2 / 3 - hue) * 6 }
        return m1
    }
    return (v(h + 1 / 3), v(h), v(h - 1 / 3))
}

// background is the dominant color, marquee text is a lighter/darker shade of it
func palette(for image: CGImage?) -> (background: NSColor, text: NSColor) {
    guard let image else {
        return (NSColor(red: 0.098, green: 0.078, blue: 0.078, alpha: 1), NSColor(white: 0.35, alpha: 1))
    }
    let c = dominantColor(image)
    let (h, l, s) = rgbToHLS((c.r / 255, c.g / 255, c.b / 255))
    let subtitleL = l > 0.5 ? max(0, l - 0.2) : min(1, l + 0.2)
    let sub = hlsToRGB(h, subtitleL, s)
    return (NSColor(srgbRed: c.r / 255, green: c.g / 255, blue: c.b / 255, alpha: 1),
            NSColor(srgbRed: sub.r, green: sub.g, blue: sub.b, alpha: 1))
}

//
//       PLAYER VIEW
//

final class PlayerView: NSView {
    var title = "Click to log in" { didSet { rebuild() } }
    var artist = "BPM Player" { didSet { rebuild() } }
    var cover: CGImage? { didSet { coverLayer.contents = cover; coverLayer.isHidden = cover == nil } }
    var textColor = NSColor(white: 0.35, alpha: 1) { didSet { rebuild() } }
    var background = NSColor(red: 0.098, green: 0.078, blue: 0.078, alpha: 1) {
        didSet { layer?.backgroundColor = background.cgColor }
    }
    var onClick: (() -> Void)?

    // what Auto currently works out to, so switching to Custom starts from the same place
    private(set) var autoSpeed: Double = 10
    private(set) var autoSize: Double = 13

    private let marqueeLayer = CALayer()
    private let coverLayer = CALayer()
    private var builtSize = NSSize.zero

    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        layer?.cornerRadius = 12
        layer?.cornerCurve = .continuous
        layer?.masksToBounds = true
        layer?.backgroundColor = background.cgColor
        layer?.addSublayer(marqueeLayer)

        coverLayer.contentsGravity = .resizeAspect
        coverLayer.cornerRadius = 3
        coverLayer.masksToBounds = true
        coverLayer.isHidden = true
        layer?.addSublayer(coverLayer)
        NotificationCenter.default.addObserver(self, selector: #selector(rebuild), name: Prefs.changed, object: nil)
    }

    required init?(coder: NSCoder) { fatalError() }

    override var mouseDownCanMoveWindow: Bool { false }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    override func layout() {
        super.layout()
        if bounds.size != builtSize { rebuild() }
    }

    // drag anywhere to move, a plain click logs in when logged out
    override func mouseDown(with event: NSEvent) {
        guard let window else { return }
        while let next = window.nextEvent(matching: [.leftMouseDragged, .leftMouseUp]) {
            if next.type == .leftMouseUp { return onClick?() ?? () }
            let moved = hypot(next.locationInWindow.x - event.locationInWindow.x,
                              next.locationInWindow.y - event.locationInWindow.y)
            if moved > 3 { return window.performDrag(with: event) }
        }
    }

    static func font(_ size: CGFloat) -> NSFont {
        NSFont(name: "Helvetica", size: size) ?? .systemFont(ofSize: size)
    }

    // Same idea as resizeFont in Marquee.js: start at 6% of the width and nudge the size
    // until the width holds the text a "nice" number of times (fractional part <= 0.5)
    static func autoFontSize(for unit: String, width: CGFloat) -> CGFloat {
        let perPoint = (unit as NSString).size(withAttributes: [.font: font(100)]).width / 100
        guard perPoint > 0 else { return width * 0.06 }
        var size = width * 0.06
        var count = width / (perPoint * size)
        var steps = 0
        while count.truncatingRemainder(dividingBy: 1) > 0.5 && steps < 20000 {
            if size > width / 20 { size = width / 30 }
            size += 0.01
            count = width / (perPoint * size)
            steps += 1
        }
        return size
    }

    @objc func rebuild() {
        let width = bounds.width, height = bounds.height
        guard width > 0, height > 0 else { return }
        builtSize = bounds.size

        CATransaction.begin()
        CATransaction.setDisableActions(true)
        marqueeLayer.frame = bounds
        marqueeLayer.sublayers?.forEach { $0.removeFromSuperlayer() }

        let titleUnit = " " + title.trimmingCharacters(in: .whitespaces) + " •"
        let artistUnit = " " + artist.trimmingCharacters(in: .whitespaces) + " •"

        autoSize = Double(PlayerView.autoFontSize(for: titleUnit, width: width))
        // original moves one window width every 30s
        autoSpeed = Double(width / 30)

        let titleSize = Prefs.sizeAuto ? autoSize : Prefs.size
        let artistSize = Prefs.sizeAuto ? Double(PlayerView.autoFontSize(for: artistUnit, width: width)) : Prefs.size
        let speed = CGFloat(Prefs.speedAuto ? autoSpeed : Prefs.speed)

        // rows alternate artist (moving left) and title (moving right) all the way down, like repeatHeight
        let titleFont = PlayerView.font(CGFloat(titleSize)), artistFont = PlayerView.font(CGFloat(artistSize))
        let spacer = max(2, 0.18 * (titleFont.pointSize + artistFont.pointSize) / 2)
        let titleHeight = titleFont.capHeight + spacer, artistHeight = artistFont.capHeight + spacer
        let pitch = titleHeight + artistHeight
        var top: CGFloat = 0
        while top < height {
            addRow(artistUnit, font: artistFont, top: top, rightward: false, speed: speed)
            addRow(titleUnit, font: titleFont, top: top + artistHeight, rightward: true, speed: speed)
            top += pitch
        }

        // album cover centered on top, half the width like the original
        let side = min(width * 0.5, height * 0.75)
        coverLayer.frame = CGRect(x: (width - side) / 2, y: (height - side) / 2, width: side, height: side)
        CATransaction.commit()
    }

    // One row is the text unit repeated enough to cover the width plus one extra unit,
    // slid by exactly one unit width per loop, so it's seamless at any size or speed
    private func addRow(_ unit: String, font: NSFont, top: CGFloat, rightward: Bool, speed: CGFloat) {
        let width = bounds.width
        let unitWidth = (unit as NSString).size(withAttributes: [.font: font]).width
        guard unitWidth > 0, speed > 0 else { return }
        let lineHeight = ceil(font.ascender - font.descender)
        let count = Int(ceil(width / unitWidth)) + 1
        let scale = window?.backingScaleFactor ?? 2

        let strip = CALayer()
        // CALayer y goes up while rows are laid out from the top, line the cap tops up with the row top
        let stripTop = top - (font.ascender - font.capHeight)
        strip.frame = CGRect(x: 0, y: bounds.height - stripTop - lineHeight, width: unitWidth * CGFloat(count), height: lineHeight)
        // text layers clip to their bounds, give descenders room below the line
        let pad = ceil(font.pointSize * 0.5)
        for i in 0..<count {
            let text = CATextLayer()
            text.string = NSAttributedString(string: unit, attributes: [.font: font, .foregroundColor: textColor])
            text.contentsScale = scale
            text.frame = CGRect(x: unitWidth * CGFloat(i), y: -pad, width: ceil(unitWidth) + 1, height: lineHeight + pad)
            strip.addSublayer(text)
        }

        let slide = CABasicAnimation(keyPath: "transform.translation.x")
        slide.fromValue = rightward ? -unitWidth : 0
        slide.toValue = rightward ? 0 : -unitWidth
        slide.duration = CFTimeInterval(unitWidth / speed)
        slide.repeatCount = .infinity
        strip.add(slide, forKey: "marquee")
        marqueeLayer.addSublayer(strip)
    }
}

//
//       PREFERENCES WINDOW
//

final class PrefsController: NSWindowController {
    let speedMode = NSSegmentedControl(labels: ["Auto", "Custom"], trackingMode: .selectOne, target: nil, action: nil)
    let speedSlider = NSSlider(value: 10, minValue: 2, maxValue: 120, target: nil, action: nil)
    let speedValue = NSTextField(labelWithString: "")
    let sizeMode = NSSegmentedControl(labels: ["Auto", "Custom"], trackingMode: .selectOne, target: nil, action: nil)
    let sizeSlider = NSSlider(value: 13, minValue: 6, maxValue: 72, target: nil, action: nil)
    let sizeValue = NSTextField(labelWithString: "")
    let accountLabel = NSTextField(labelWithString: "")
    let accountButton = NSButton(title: "", target: nil, action: nil)

    let player: PlayerView
    let spotify: Spotify
    var onAccountChange: (() -> Void)?

    init(player: PlayerView, spotify: Spotify) {
        self.player = player
        self.spotify = spotify
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 420, height: 150),
                              styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = "BPM Player Preferences"
        super.init(window: window)

        for control in [speedMode, sizeMode, speedSlider, sizeSlider] as [NSControl] {
            control.target = self
            control.action = #selector(changed(_:))
        }
        accountButton.target = self
        accountButton.action = #selector(toggleAccount)
        for slider in [speedSlider, sizeSlider] {
            slider.isContinuous = true
            slider.widthAnchor.constraint(equalToConstant: 170).isActive = true
        }
        for label in [speedValue, sizeValue] {
            label.font = .monospacedDigitSystemFont(ofSize: 12, weight: .regular)
            label.widthAnchor.constraint(equalToConstant: 60).isActive = true
        }

        let grid = NSGridView(views: [
            [NSTextField(labelWithString: "Marquee speed:"), speedMode, speedSlider, speedValue],
            [NSTextField(labelWithString: "Text size:"), sizeMode, sizeSlider, sizeValue],
            [NSTextField(labelWithString: "Spotify:"), accountLabel, accountButton, NSGridCell.emptyContentView],
        ])
        grid.rowSpacing = 12
        grid.columnSpacing = 10
        grid.column(at: 0).xPlacement = .trailing
        grid.rowAlignment = .firstBaseline
        grid.translatesAutoresizingMaskIntoConstraints = false

        let content = NSView()
        content.addSubview(grid)
        NSLayoutConstraint.activate([
            grid.topAnchor.constraint(equalTo: content.topAnchor, constant: 20),
            grid.bottomAnchor.constraint(equalTo: content.bottomAnchor, constant: -20),
            grid.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 20),
            grid.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -20),
        ])
        window.contentView = content
        window.center()
    }

    required init?(coder: NSCoder) { fatalError() }

    func show() {
        refresh()
        NSApp.activate(ignoringOtherApps: true)
        window?.makeKeyAndOrderFront(nil)
    }

    func refresh() {
        speedMode.selectedSegment = Prefs.speedAuto ? 0 : 1
        sizeMode.selectedSegment = Prefs.sizeAuto ? 0 : 1
        speedSlider.doubleValue = Prefs.speedAuto ? player.autoSpeed : Prefs.speed
        sizeSlider.doubleValue = Prefs.sizeAuto ? player.autoSize : Prefs.size
        speedSlider.isEnabled = !Prefs.speedAuto
        sizeSlider.isEnabled = !Prefs.sizeAuto
        speedValue.stringValue = String(format: "%.0f pt/s", speedSlider.doubleValue)
        sizeValue.stringValue = String(format: "%.1f pt", sizeSlider.doubleValue)
        accountLabel.stringValue = spotify.isLoggedIn ? "Logged in" : "Not logged in"
        accountButton.title = spotify.isLoggedIn ? "Log Out" : "Log In…"
    }

    @objc func changed(_ sender: NSControl) {
        // switching to Custom starts from whatever Auto was showing, so nothing jumps
        if sender === speedMode {
            Prefs.speedAuto = speedMode.selectedSegment == 0
            if !Prefs.speedAuto { Prefs.speed = player.autoSpeed }
        } else if sender === sizeMode {
            Prefs.sizeAuto = sizeMode.selectedSegment == 0
            if !Prefs.sizeAuto { Prefs.size = player.autoSize }
        } else if sender === speedSlider {
            Prefs.speed = speedSlider.doubleValue
        } else if sender === sizeSlider {
            Prefs.size = sizeSlider.doubleValue
        }
        NotificationCenter.default.post(name: Prefs.changed, object: nil)
        refresh()
    }

    @objc func toggleAccount() {
        if spotify.isLoggedIn { spotify.logout() } else { spotify.login() }
        onAccountChange?()
        refresh()
    }
}

//
//       APP
//

final class WidgetPanel: NSPanel {
    // borderless panels refuse key status by default
    override var canBecomeKey: Bool { true }

    // the app never activates (so it doesn't steal focus), send shortcuts to the menu ourselves
    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        NSApp.mainMenu?.performKeyEquivalent(with: event) ?? super.performKeyEquivalent(with: event)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    var panel: WidgetPanel!
    var player: PlayerView!
    var statusItem: NSStatusItem!
    var prefs: PrefsController!
    var spotify: Spotify!
    var current: Track?
    var pollTimer: Timer?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let clientID = Bundle.main.object(forInfoDictionaryKey: "SpotifyClientID") as? String ?? ""
        spotify = Spotify(clientID: clientID)
        spotify.onLogin = { [weak self] in self?.poll() }

        buildWindow()
        prefs = PrefsController(player: player, spotify: spotify)
        prefs.onAccountChange = { [weak self] in self?.poll() }
        buildMenus()
        poll()
    }

    func buildWindow() {
        panel = WidgetPanel(contentRect: NSRect(origin: .zero, size: defaultSize),
                            styleMask: [.borderless, .resizable, .nonactivatingPanel],
                            backing: .buffered, defer: false)
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isFloatingPanel = true
        panel.hidesOnDeactivate = false
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.minSize = NSSize(width: 100, height: 100)

        player = PlayerView(frame: NSRect(origin: .zero, size: defaultSize))
        player.onClick = { [weak self] in
            guard let self, !self.spotify.isLoggedIn else { return }
            self.spotify.login()
        }
        panel.contentView = player

        // remember where you put it, first launch goes to the top right corner
        if !panel.setFrameUsingName("BPMPlayer"), let screen = NSScreen.main?.visibleFrame {
            panel.setFrameOrigin(NSPoint(x: screen.maxX - defaultSize.width - 16, y: screen.maxY - defaultSize.height - 16))
        }
        panel.setFrameAutosaveName("BPMPlayer")
        panel.orderFrontRegardless()
        panel.invalidateShadow()
    }

    func buildMenus() {
        // menu bar icon, there's no Dock icon
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        statusItem.button?.image = NSImage(systemSymbolName: "music.note", accessibilityDescription: "BPM Player")
        statusItem.menu = makeMenu()
        player.menu = makeMenu()

        // gives Cmd+, / Cmd+W / Cmd+Q while the widget is focused
        let appItem = NSMenuItem()
        appItem.submenu = makeMenu()
        NSApp.mainMenu = NSMenu()
        NSApp.mainMenu?.addItem(appItem)
    }

    func makeMenu() -> NSMenu {
        let menu = NSMenu()
        menu.delegate = self
        menu.addItem(withTitle: "Show / Hide Widget", action: #selector(toggleWidget), keyEquivalent: "w").target = self
        menu.addItem(withTitle: "Preferences…", action: #selector(showPrefs), keyEquivalent: ",").target = self
        menu.addItem(withTitle: "", action: #selector(toggleAccount), keyEquivalent: "").target = self
        menu.addItem(.separator())
        menu.addItem(withTitle: "Quit BPM Player", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        return menu
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.items.first { $0.action == #selector(toggleAccount) }?.title = spotify.isLoggedIn ? "Log Out" : "Log In…"
    }

    @objc func toggleWidget() {
        if panel.isVisible { panel.orderOut(nil) } else { panel.orderFrontRegardless() }
    }

    @objc func showPrefs() {
        prefs.show()
    }

    @objc func toggleAccount() {
        prefs.toggleAccount()
    }

    //
    //       POLLING
    //

    func poll() {
        pollTimer?.invalidate()
        spotify.currentlyPlaying { [weak self] playback in
            guard let self else { return }
            switch playback {
            case .playing(let track):
                if track.id != self.current?.id { self.show(track) }
                self.current = track
                // check often enough to catch skips, and right as the song ends
                self.schedule(min(3, track.remaining + 0.3))
            case .nothing:
                self.current = nil
                self.showPlaceholder("Nothing playing", "Spotify")
                self.schedule(10)
            case .loggedOut:
                self.current = nil
                self.showPlaceholder("Click to log in", "BPM Player")
            case .failed(let retryAfter):
                self.schedule(max(3, retryAfter))
            }
        }
    }

    func schedule(_ seconds: TimeInterval) {
        pollTimer?.invalidate()
        pollTimer = Timer.scheduledTimer(withTimeInterval: seconds, repeats: false) { [weak self] _ in self?.poll() }
    }

    func showPlaceholder(_ title: String, _ artist: String) {
        guard player.title != title || player.artist != artist || player.cover != nil else { return }
        let colors = palette(for: nil)
        player.cover = nil
        player.background = colors.background
        player.textColor = colors.text
        player.title = title
        player.artist = artist
    }

    func show(_ track: Track) {
        guard let url = track.imageURL else {
            showPlaceholder(track.title, track.artist)
            return
        }
        URLSession.shared.dataTask(with: url) { [weak self] data, _, _ in
            let image = data.flatMap { NSImage(data: $0)?.cgImage(forProposedRect: nil, context: nil, hints: nil) }
            let colors = palette(for: image)
            DispatchQueue.main.async {
                guard let self, self.current?.id == track.id else { return }
                self.player.cover = image
                self.player.background = colors.background
                self.player.textColor = colors.text
                self.player.title = track.title
                self.player.artist = track.artist
            }
        }.resume()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
