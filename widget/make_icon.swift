// Draws the app icon (a mini version of the player: marquee rows behind a music note)
// Usage: swift make_icon.swift <output.iconset>
import Cocoa

let out = CommandLine.arguments[1]
try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)

func draw(_ px: Int) -> Data {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                               bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let s = CGFloat(px) / 1024

    // standard macOS icon grid: 824pt rounded square centered in 1024
    let tile = NSRect(x: 100 * s, y: 100 * s, width: 824 * s, height: 824 * s)
    let shape = NSBezierPath(roundedRect: tile, xRadius: 185 * s, yRadius: 185 * s)
    NSGradient(starting: NSColor(srgbRed: 0.36, green: 0.70, blue: 0.85, alpha: 1),
               ending: NSColor(srgbRed: 0.16, green: 0.42, blue: 0.62, alpha: 1))!.draw(in: shape, angle: -90)

    // marquee rows
    shape.addClip()
    let font = NSFont(name: "Helvetica-Bold", size: 92 * s) ?? .boldSystemFont(ofSize: 92 * s)
    let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: NSColor(white: 1, alpha: 0.16)]
    var y = tile.maxY - 110 * s
    var row = 0
    while y > tile.minY - 100 * s {
        let text = String(repeating: row % 2 == 0 ? "BPM • " : "PLAY • ", count: 6) as NSString
        text.draw(at: NSPoint(x: tile.minX - CGFloat(row % 2) * 120 * s, y: y), withAttributes: attrs)
        y -= 100 * s
        row += 1
    }

    // cover square with a note
    let cover = NSRect(x: 312 * s, y: 312 * s, width: 400 * s, height: 400 * s)
    let shadow = NSShadow()
    shadow.shadowBlurRadius = 30 * s
    shadow.shadowOffset = NSSize(width: 0, height: -10 * s)
    shadow.shadowColor = NSColor(white: 0, alpha: 0.35)
    shadow.set()
    NSColor(srgbRed: 0.10, green: 0.08, blue: 0.08, alpha: 1).setFill()
    NSBezierPath(roundedRect: cover, xRadius: 24 * s, yRadius: 24 * s).fill()
    NSShadow().set()

    let config = NSImage.SymbolConfiguration(pointSize: 220 * s, weight: .semibold)
    if let note = NSImage(systemSymbolName: "music.note", accessibilityDescription: nil)?.withSymbolConfiguration(config) {
        let tinted = NSImage(size: note.size, flipped: false) { rect in
            note.draw(in: rect)
            NSColor(srgbRed: 0.36, green: 0.80, blue: 0.95, alpha: 1).set()
            rect.fill(using: .sourceAtop)
            return true
        }
        let size = note.size
        tinted.draw(in: NSRect(x: cover.midX - size.width / 2, y: cover.midY - size.height / 2, width: size.width, height: size.height))
    }

    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:])!
}

// stops at 512px, the Dock never shows it bigger and it keeps the app small
for base in [16, 32, 128, 256] {
    try! draw(base).write(to: URL(fileURLWithPath: "\(out)/icon_\(base)x\(base).png"))
    try! draw(base * 2).write(to: URL(fileURLWithPath: "\(out)/icon_\(base)x\(base)@2x.png"))
}
try! draw(512).write(to: URL(fileURLWithPath: "\(out)/icon_512x512.png"))
