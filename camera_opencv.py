import datetime
import cv2
import numpy as np
import tracker
from AIDetector_pytorch import Detector
from base_camera import BaseCamera

class Camera(BaseCamera):
    @staticmethod
    def set_video_source(source):
        Camera.video_source = source

    @staticmethod
    def frames():
        # 根据视频尺寸，填充一个polygon，供撞线计算使用
        mask_image_temp = np.zeros((1080, 1920), dtype=np.uint8)

        # 初始化2个撞线polygon
        list_pts_blue = [[0, 500], [1900, 500], [1900, 640], [0, 640]]
        ndarray_pts_blue = np.array(list_pts_blue, np.int32)
        polygon_blue_value_1 = cv2.fillPoly(mask_image_temp, [ndarray_pts_blue], color=1)
        polygon_blue_value_1 = polygon_blue_value_1[:, :, np.newaxis]

        # 填充第二个polygon
        width = 1920
        height = 1080
        mask_image_temp = np.zeros((height, width), dtype=np.uint8)
        list_pts_yellow = [[0, 650], [1900, 650], [1900, 800], [0, 800]]
        ndarray_pts_yellow = np.array(list_pts_yellow, np.int32)
        polygon_yellow_value_2 = cv2.fillPoly(mask_image_temp, [ndarray_pts_yellow], color=2)
        polygon_yellow_value_2 = polygon_yellow_value_2[:, :, np.newaxis]

        # 撞线检测用mask，包含2个polygon，（值范围 0、1、2），供撞线计算使用
        polygon_mask_blue_and_yellow = polygon_blue_value_1 + polygon_yellow_value_2

        # 缩小尺寸，1920x1080->960x540
        polygon_mask_blue_and_yellow = cv2.resize(polygon_mask_blue_and_yellow, (960, 540))

        # 蓝 色盘 b,g,r
        blue_color_plate = [255, 0, 0]
        # 蓝 polygon图片
        blue_image = np.array(polygon_blue_value_1 * blue_color_plate, np.uint8)

        # 黄 色盘
        yellow_color_plate = [0, 255, 255]
        # 黄 polygon图片
        yellow_image = np.array(polygon_yellow_value_2 * yellow_color_plate, np.uint8)

        # 彩色图片（值范围 0-255）
        color_polygons_image = blue_image + yellow_image
        # 缩小尺寸，1920x1080->960x540
        color_polygons_image = cv2.resize(color_polygons_image, (960, 540))

        # list 与蓝色polygon重叠
        list_overlapping_blue_polygon = []

        # list 与黄色polygon重叠
        list_overlapping_yellow_polygon = []

        # 进入数量
        down_count = 0
        # 离开数量
        up_count = 0

        font_draw_number = cv2.FONT_HERSHEY_SIMPLEX
        draw_text_postion = (int(960 * 0.01), int(540 * 0.05))
        # 初始化 yolov5
        detector = Detector()
        # 打开视频
        #capture = cv2.VideoCapture(0)
        capture = cv2.VideoCapture("testVideo.mp4")
        videoWriter = None
        fps = int(capture.get(5))
        startTime = ""
        VideoNumber = 1;
        while True:
            # 读取每帧图片
            _, im = capture.read()
            if im is None:
                break

            # 缩小尺寸，1920x1080->960x540
            im = cv2.resize(im, (960, 540))

            list_bboxs = []
            # 更新跟踪器
            output_image_frame, list_bboxs = tracker.update(detector, im)
            # 输出图片
            output_image_frame = cv2.add(output_image_frame, color_polygons_image)

            if len(list_bboxs) > 0:
                # ----------------------判断撞线----------------------
                for item_bbox in list_bboxs:
                    x1, y1, x2, y2, label, track_id = item_bbox

                    # 撞线检测点，(x1，y1)，y方向偏移比例 0.0~1.0
                    y1_offset = int(y1 + ((y2 - y1) * 0.06))

                    # 撞线的点
                    y = y1_offset
                    x = x1

                    if polygon_mask_blue_and_yellow[y, x] == 1:
                        # 如果撞 蓝polygon
                        if track_id not in list_overlapping_blue_polygon:
                            list_overlapping_blue_polygon.append(track_id)
                        pass

                        # 判断 黄polygon list 里是否有此 track_id
                        # 有此 track_id，则 认为是 外出方向
                        if track_id in list_overlapping_yellow_polygon:
                            # 外出+1
                            up_count += 1

                            print(
                                f'类别: {label} | id: {track_id} | 上行撞线 | 上行撞线总数: {up_count} | 上行id列表: {list_overlapping_yellow_polygon}')

                            # 删除 黄polygon list 中的此id
                            list_overlapping_yellow_polygon.remove(track_id)

                            pass
                        else:
                            # 无此 track_id，不做其他操作
                            pass

                    elif polygon_mask_blue_and_yellow[y, x] == 2:
                        # 如果撞 黄polygon
                        if track_id not in list_overlapping_yellow_polygon:
                            list_overlapping_yellow_polygon.append(track_id)
                        pass

                        # 判断 蓝polygon list 里是否有此 track_id
                        # 有此 track_id，则 认为是 进入方向
                        if track_id in list_overlapping_blue_polygon:
                            # 进入+1
                            down_count += 1

                            print(
                                f'类别: {label} | id: {track_id} | 下行撞线 | 下行撞线总数: {down_count} | 下行id列表: {list_overlapping_blue_polygon}')

                            # 删除 蓝polygon list 中的此id
                            list_overlapping_blue_polygon.remove(track_id)

                            pass
                        else:
                            # 无此 track_id，不做其他操作
                            pass
                        pass
                    else:
                        pass
                    pass

                pass

                # ----------------------清除无用id----------------------
                list_overlapping_all = list_overlapping_yellow_polygon + list_overlapping_blue_polygon
                for id1 in list_overlapping_all:
                    is_found = False
                    for _, _, _, _, _, bbox_id in list_bboxs:
                        if bbox_id == id1:
                            is_found = True
                            break
                        pass
                    pass

                    if not is_found:
                        # 如果没找到，删除id
                        if id1 in list_overlapping_yellow_polygon:
                            list_overlapping_yellow_polygon.remove(id1)
                        pass
                        if id1 in list_overlapping_blue_polygon:
                            list_overlapping_blue_polygon.remove(id1)
                        pass
                    pass
                list_overlapping_all.clear()
                pass

                # 清空list
                list_bboxs.clear()

                pass
            else:
                # 如果图像中没有任何的bbox，则清空list
                list_overlapping_blue_polygon.clear()
                list_overlapping_yellow_polygon.clear()
                pass
            pass
            time_now = datetime.datetime.now()
            strData = time_now.strftime('%y%m%d')
            strTime = time_now.strftime('%H%M%S')
            path = strData + "_" + strTime;
            text_draw = 'IN: ' + str(down_count) + \
                        ' , OUT: ' + str(up_count) + \
                        ', Time: ' + path
            output_image_frame = cv2.putText(img=output_image_frame, text=text_draw,
                                             org=draw_text_postion,
                                             fontFace=font_draw_number,
                                             fontScale=1, color=(255, 255, 255), thickness=2)

            if videoWriter is None:
                fourcc = cv2.VideoWriter_fourcc('X', '2', '6', '4')
                FileName ="static/recording/" + str(VideoNumber) + '.mp4'
                VideoNumber = VideoNumber + 1;
                if VideoNumber > 10 :
                    VideoNumber = 1;
                videoWriter = cv2.VideoWriter(FileName, fourcc, fps,
                                              (output_image_frame.shape[1], output_image_frame.shape[0]))
                startTime = strTime
                print(FileName)
            videoWriter.write(output_image_frame)
            if int(datetime.datetime.now().strftime('%H%M%S')) - int(startTime) > 600:
                print("save the video")
                videoWriter = None
            # global frame_queue
            frame_resized = cv2.resize(output_image_frame, (width // 2, height // 2))
            yield cv2.imencode('.jpg', frame_resized)[1].tobytes()
            # cv2.imshow('demo', output_image_frame)
            cv2.waitKey(1)

            pass
        pass

        capture.release()
        cv2.destroyAllWindows()
