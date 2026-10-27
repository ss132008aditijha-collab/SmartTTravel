"""
SmartTravel - Standalone Pure-Python PDF Generator
Generates valid, professional PDF 1.4 E-Tickets with styling, borders,
headers, passenger grids, fare summaries, and verification marks.
Requires zero external dependencies.
"""

def escape_pdf_text(text):
    if text is None:
        return ""
    text = str(text)
    # PDF literal string escaping: \ -> \\, ( -> \(, ) -> \)
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text


def generate_ticket_pdf(booking_data):
    """
    Takes a dictionary of booking details and returns bytes of a clean PDF 1.4 file.
    """
    transport = str(booking_data.get("transport", "train")).lower()
    is_train = transport == "train"

    booking_id = escape_pdf_text(booking_data.get("booking_id", "ST999999"))
    vehicle_name = escape_pdf_text(booking_data.get("name") or booking_data.get("vehicle_name", "Express"))
    vehicle_number = escape_pdf_text(booking_data.get("number") or booking_data.get("vehicle_number", "12627"))
    source = escape_pdf_text(booking_data.get("source", "Bengaluru"))
    destination = escape_pdf_text(booking_data.get("destination", "Chennai"))
    journey_date = escape_pdf_text(booking_data.get("journey_date") or booking_data.get("date", "2026-10-30"))
    boarding = escape_pdf_text(booking_data.get("boarding", "Main Station"))
    seat = escape_pdf_text(booking_data.get("seat", "A1"))
    passenger_name = escape_pdf_text(booking_data.get("passenger_name", "Valued Passenger"))
    age = escape_pdf_text(booking_data.get("age", "28"))
    gender = escape_pdf_text(booking_data.get("gender", "Female"))
    phone = escape_pdf_text(booking_data.get("phone", "9876543210"))
    email = escape_pdf_text(booking_data.get("email", "guest@smarttravel.com"))
    price = float(booking_data.get("price") or booking_data.get("ticket_price", 0))
    food_total = float(booking_data.get("food_total", 0))
    total = float(booking_data.get("total", price + food_total))
    vehicle_class = escape_pdf_text(booking_data.get("vehicle_class", "3A (AC 3 Tier)" if is_train else "AC Sleeper"))
    quota = escape_pdf_text(booking_data.get("quota", "GENERAL"))
    status = escape_pdf_text(booking_data.get("status", "CONFIRMED"))

    # Determine coach & berth display
    if is_train:
        if "EC" in vehicle_class:
            coach_berth = f"Coach E1  |  Seat {seat}"
        elif "CC" in vehicle_class:
            coach_berth = f"Coach C1  |  Seat {seat}"
        elif "1A" in vehicle_class:
            coach_berth = f"Coach H1  |  Berth {seat}"
        elif "2A" in vehicle_class:
            coach_berth = f"Coach A2  |  Berth {seat}"
        elif "3E" in vehicle_class:
            coach_berth = f"Coach M1  |  Berth {seat}"
        elif "SL" in vehicle_class:
            coach_berth = f"Coach S4  |  Berth {seat}"
        else:
            coach_berth = f"Coach B4  |  Berth {seat}"
    else:
        coach_berth = f"Seat / Berth: {seat}"

    commands = []

    # Helper: draw filled rectangle
    def fill_rect(x, y, w, h, r, g, b):
        commands.append(f"{r:.3f} {g:.3f} {b:.3f} rg\n{x:.1f} {y:.1f} {w:.1f} {h:.1f} re\nf\n")

    # Helper: draw stroke rectangle
    def stroke_rect(x, y, w, h, r, g, b, line_w=1):
        commands.append(f"{r:.3f} {g:.3f} {b:.3f} RG\n{line_w} w\n{x:.1f} {y:.1f} {w:.1f} {h:.1f} re\nS\n")

    # Helper: draw text
    def draw_text(x, y, text, font="F1", size=10, r=0.1, g=0.1, b=0.1):
        commands.append(f"BT\n/{font} {size} Tf\n{r:.3f} {g:.3f} {b:.3f} rg\n{x:.1f} {y:.1f} Td\n({text}) Tj\nET\n")

    # Page size: A4 (595.28 x 841.89 points)
    # Background card border
    stroke_rect(30, 40, 535, 760, 0.8, 0.85, 0.9, 1.5)

    # 1. HEADER BANNER
    if is_train:
        fill_rect(30, 725, 535, 75, 0.08, 0.18, 0.45) # Navy Blue
        header_title = "SMARTTRAVEL - ELECTRONIC DEMO RESERVATION SLIP"
        sub_title = "ACADEMIC PROTOTYPE & DEMO BOOKING -- NOT AN OFFICIAL OPERATOR TICKET"
    else:
        fill_rect(30, 725, 535, 75, 0.01, 0.45, 0.75) # Sky Teal
        header_title = "SMARTTRAVEL - INTERCITY BUS DEMO TRAVEL PASS"
        sub_title = "ACADEMIC PROTOTYPE & DEMO BOOKING -- NOT AN OFFICIAL OPERATOR TICKET"

    draw_text(48, 770, header_title, font="F2", size=13, r=1, g=1, b=1)
    draw_text(48, 752, sub_title, font="F1", size=7.8, r=0.88, g=0.92, b=1)
    draw_text(48, 736, "ACADEMIC SIMULATION * VERIFIED DEMO FARE & SEAT SNAPSHOT", font="F2", size=8, r=0.75, g=0.95, b=0.75)

    # 2. PNR & STATUS STRIP
    fill_rect(30, 680, 535, 45, 0.96, 0.97, 0.99)
    stroke_rect(30, 680, 535, 45, 0.88, 0.9, 0.93, 1)

    pnr_label = "SMARTTRAVEL DEMO BOOKING REF:"
    draw_text(48, 706, pnr_label, font="F1", size=8.5, r=0.4, g=0.45, b=0.5)
    draw_text(48, 690, booking_id, font="F2", size=13.5, r=0.1, g=0.25, b=0.6)

    # Status Pill
    fill_rect(410, 689, 135, 26, 0.06, 0.65, 0.35)
    draw_text(424, 698, f"STATUS: {status}", font="F2", size=10, r=1, g=1, b=1)

    # 3. JOURNEY ORIGIN -> DESTINATION BANNER
    fill_rect(48, 605, 499, 62, 0.93, 0.95, 0.99)
    stroke_rect(48, 605, 499, 62, 0.75, 0.82, 0.95, 1)

    draw_text(60, 650, "ORIGIN (DEPARTURE)", font="F1", size=8, r=0.45, g=0.5, b=0.6)
    draw_text(60, 630, source, font="F2", size=16, r=0.08, g=0.15, b=0.35)
    draw_text(60, 614, f"Boarding: {boarding}", font="F1", size=8.5, r=0.25, g=0.3, b=0.35)

    draw_text(268, 633, "------->", font="F2", size=14, r=0.1, g=0.4, b=0.8)

    draw_text(370, 650, "DESTINATION (ARRIVAL)", font="F1", size=8, r=0.45, g=0.5, b=0.6)
    draw_text(370, 630, destination, font="F2", size=16, r=0.08, g=0.15, b=0.35)
    draw_text(370, 614, "Drop: Central Terminus", font="F1", size=8.5, r=0.25, g=0.3, b=0.35)

    # 4. RESERVATION DETAILS TABLE (2 Columns)
    y_start = 575
    row_height = 28

    details_col1 = [
        ("Vehicle Name:", vehicle_name),
        ("Vehicle Number:", f"#{vehicle_number}"),
        ("Travel Date:", f"{journey_date}"),
        ("Travel Class:", vehicle_class),
        ("Quota:", quota)
    ]

    details_col2 = [
        ("Coach & Berth / Seat:", coach_berth),
        ("Passenger Name:", passenger_name),
        ("Age & Gender:", f"{age} Yrs / {gender}"),
        ("Mobile Number:", phone),
        ("Payment Mode:", "UPI / Instant Demo")
    ]

    # Column 1
    y = y_start
    for label, val in details_col1:
        draw_text(50, y, label, font="F1", size=9, r=0.45, g=0.5, b=0.55)
        draw_text(160, y, val, font="F2", size=9.5, r=0.08, g=0.12, b=0.18)
        # Subtle horizontal divider
        commands.append(f"0.92 0.93 0.95 RG\n0.5 w\n50 {y - 6} m 280 {y - 6} l\nS\n")
        y -= row_height

    # Column 2
    y = y_start
    for label, val in details_col2:
        draw_text(305, y, label, font="F1", size=9, r=0.45, g=0.5, b=0.55)
        # Highlight seat
        color_r, color_g, color_b = (0.08, 0.45, 0.8) if "Coach" in label or "Seat" in label else (0.08, 0.12, 0.18)
        draw_text(420, y, val, font="F2", size=9.5, r=color_r, g=color_g, b=color_b)
        commands.append(f"0.92 0.93 0.95 RG\n0.5 w\n305 {y - 6} m 545 {y - 6} l\nS\n")
        y -= row_height

    # 5. DASHED PERFORATION LINE
    commands.append(f"0.7 0.75 0.8 RG\n1 w\n[4 4] 0 d\n40 420 m 555 420 l\nS\n[] 0 d\n")

    # 6. FARE SUMMARY SECTION
    draw_text(50, 395, "OFFICIAL FARE & GST RECEIPT", font="F2", size=10, r=0.2, g=0.25, b=0.3)

    fare_items = [
        ("Base Ticket Fare (" + vehicle_class + "):", f"Rs. {price:.2f}"),
        ("Pre-Ordered Catering / Meals:", f"Rs. {food_total:.2f}"),
        ("Convenience Charges & GST (Zero Fee):", "Rs. 0.00"),
    ]

    fy = 375
    for flabel, fval in fare_items:
        draw_text(50, fy, flabel, font="F1", size=9, r=0.35, g=0.4, b=0.45)
        draw_text(240, fy, fval, font="F2", size=9.5, r=0.1, g=0.1, b=0.1)
        fy -= 18

    # Total Box
    fill_rect(50, fy - 10, 260, 26, 0.94, 0.97, 1)
    stroke_rect(50, fy - 10, 260, 26, 0.6, 0.75, 0.95, 1)
    draw_text(60, fy - 2, "TOTAL AMOUNT PAID:", font="F2", size=10, r=0.1, g=0.25, b=0.6)
    draw_text(220, fy - 2, f"Rs. {total:.2f}", font="F2", size=11, r=0.08, g=0.55, b=0.25)

    # 7. QR CODE & VERIFICATION BOX
    stroke_rect(350, 280, 195, 125, 0.8, 0.85, 0.9, 1)
    fill_rect(350, 385, 195, 20, 0.95, 0.96, 0.98)
    draw_text(375, 391, "DIGITAL BOARDING PASS", font="F2", size=8.5, r=0.3, g=0.35, b=0.4)

    # Simulated QR Pattern (sharp pixel cells)
    qr_x, qr_y = 365, 290
    qr_cell = 4.2
    # Corner finders
    for fx, fy in [(qr_x, qr_y + 55), (qr_x + 60, qr_y + 55), (qr_x, qr_y)]:
        fill_rect(fx, fy, 24, 24, 0.1, 0.15, 0.25)
        fill_rect(fx + 4, fy + 4, 16, 16, 1, 1, 1)
        fill_rect(fx + 8, fy + 8, 8, 8, 0.1, 0.15, 0.25)

    # Decorative barcode bars
    for b_idx in range(15):
        bw = 2 if b_idx % 2 == 0 else 1
        bx = 475 + b_idx * 4.5
        fill_rect(bx, 295, bw, 65, 0.1, 0.15, 0.25)

    draw_text(365, 283, f"VERIFIED: {booking_id}", font="F2", size=7.5, r=0.4, g=0.45, b=0.5)

    # 8. PASSENGER TRAVEL INSTRUCTIONS & LEGAL NOTICE
    fill_rect(48, 70, 499, 185, 0.97, 0.98, 0.99)
    stroke_rect(48, 70, 499, 185, 0.85, 0.88, 0.92, 1)

    draw_text(60, 238, "SMARTTRAVEL DEMO BOOKING NOTICE & PASSENGER GUIDELINES", font="F2", size=8.5, r=0.15, g=0.2, b=0.25)

    rules = [
        "1. DEMO DISCLAIMER: This is an educational demonstration slip generated for a college mini-project simulation.",
        "   Simulated demo payment was processed. It does not constitute a physical reservation with transport operators.",
        "2. PHOTO IDENTITY: During real journeys, passengers must carry Government photo ID (Aadhaar / Voter ID / Passport).",
        "3. REPORTING TIME: Recommended reporting at designated boarding points is 20 minutes prior to scheduled departure.",
        "4. CANCELLATION: Bookings can be cancelled via the SmartTravel portal prior to departure with demo refund credit.",
        "5. SYSTEM ARCHITECTURE: 100% Local SQLite database catalog with verified realistic demo schedules."
    ]

    ry = 218
    for rule in rules:
        draw_text(60, ry, rule, font="F1", size=7.2, r=0.35, g=0.4, b=0.45)
        ry -= 18

    # Footer note
    draw_text(160, 50, "SmartTravel Academic Project -- Hybrid Transport Information & Demo Reservation System", font="F2", size=8, r=0.3, g=0.35, b=0.4)

    # ASSEMBLE PDF 1.4 OBJECTS
    content_stream = "".join(commands)
    stream_bytes = content_stream.encode("latin1")
    stream_length = len(stream_bytes)

    objects = []
    # 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: Page (A4: 595.28 x 841.89)
    objects.append(
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Contents 4 0 R\n"
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >>\n"
        b">>\nendobj\n"
    )
    # 4: Content Stream
    objects.append(
        f"4 0 obj\n<< /Length {stream_length} >>\nstream\n".encode("latin1") +
        stream_bytes +
        b"\nendstream\nendobj\n"
    )
    # 5: Standard Font (Helvetica)
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    # 6: Bold Font (Helvetica-Bold)
    objects.append(b"6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")

    out = [b"%PDF-1.4\n"]
    offsets = []
    curr = len(out[0])
    for obj in objects:
        offsets.append(curr)
        out.append(obj)
        curr += len(obj)

    xref_offset = curr
    out.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1"))
    for off in offsets:
        out.append(f"{off:010d} 00000 n \n".encode("latin1"))
    out.append(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1"))

    return b"".join(out)
