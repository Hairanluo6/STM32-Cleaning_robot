import sensor, image, time
from pyb import UART

red_threshold = (24, 35, 10, 33, -11, 15)
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(10)
sensor.set_auto_whitebal(False)
#sensor.set_auto_exposure(False, exposure_us=42000)  #  固定曝光
sensor.set_auto_exposure(True)

uart = UART(3, 115200)
uart.init(9600, bits=8, parity=None, stop=1)

#  新阈值（后面要重新标定）
size_threshold = 40   # 用高度，不再用面积

#  滤波变量
x_filtered = 0
h_filtered = 0
lost_count = 0

alpha = 0.25   # 平滑系数（比你原来更稳）

def find_max(blobs):
    max_blob = None
    max_size = 0
    for blob in blobs:
        if blob.pixels() > max_size:
            max_blob = blob
            max_size = blob.pixels()
    return max_blob

while(True):
    img = sensor.snapshot()

    blobs = img.find_blobs([red_threshold],
                           pixels_threshold=35,   #  提高一点抗噪
                           area_threshold=20,
                           merge=True)

    if blobs:
        max_blob = find_max(blobs)

        if max_blob and max_blob.pixels() > 80:   #  提高过滤门槛
            lost_count = 0

            #  水平误差（不变）
            x_error = max_blob.cx() - img.width()/2

            #  距离改成“高度 + 面积融合”
            h1 = max_blob.h() * 20          # 高度权重（主要）
            h2 = max_blob.pixels() * 0.02   # 面积辅助（微调）

            distance_value = h1 + h2

            h_error = distance_value - size_threshold

            #  滤波（关键）
            x_filtered = (1-alpha)*x_filtered + alpha*x_error
            h_filtered = (1-alpha)*h_filtered + alpha*h_error

            #  可视化
            img.draw_rectangle(max_blob.rect())
            img.draw_cross(max_blob.cx(), max_blob.cy())

            #  发送
            output_str = "[%d,%d]" % (int(x_filtered), int(h_filtered))
            print("Postition:", output_str)
            uart.write((output_str + "\r\n").encode())

    else:
        lost_count += 1
        if lost_count > 5:
            uart.write("[0,0]\r\n")

    time.sleep_ms(10)
