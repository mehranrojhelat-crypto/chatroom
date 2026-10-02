import qrcode
from qrcode.constants import ERROR_CORRECT_H
from qrcode.image.svg import SvgPathImage
from pathlib import Path

def create_resistant_qr(data: str, filename: str, fmt: str = "png") -> str:
    """
    ساخت QR مقاوم به خطا
    fmt: "png" یا "svg"
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,  # بالاترین سطح مقاومت
        box_size=12,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    base_dir = Path(__file__).parent
    qr_dir = base_dir / "static" / "qrcodes"
    qr_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "svg":
        img = qr.make_image(image_factory=SvgPathImage)
        file_path = qr_dir / f"{filename}.svg"
        img.save(file_path)
    else:
        # کیفیت بالا برای PNG
        qr.box_size = 20          # کیفیت بالاتر
        img = qr.make_image(fill_color="black", back_color="white")
        file_path = qr_dir / f"{filename}.png"
        img.save(file_path)

    print(f"QR ذخیره شد در: {file_path}")
    return str(file_path)