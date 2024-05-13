import numpy as np
import mediapipe as mp
import cv2 
import csv

def main():
    hand_signals = ['FW', 'ST', 'RL', 'RR', 'BW']
    font = cv2.FONT_HERSHEY_SIMPLEX

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands = 2, min_detection_confidence = 0.8, min_tracking_confidence = 0.5)
    mp_draw = mp.solutions.drawing_utils
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    mode = 0
    number = -1
    while cap.isOpened():
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        if not ret:
            continue
        key = cv2.waitKey(10)
        if (key == 27): #Press ESC to exit
            break
        number, mode = select_signals(key, number, mode, len(hand_signals))
        cv2.putText(frame, 'Current hand signal for recording: {} - {}'.format(str(number), str(hand_signals[number])), (0, 200), font, 1, (0,255,255), 2, cv2.LINE_AA)
        if mode == 0:
            cv2.putText(frame, 'Press I to start capturing hand gesture.', (0, 100), font, 1, (0,255,255), 2, cv2.LINE_AA)
        elif mode == 1:
            cv2.putText(frame, 'Currently recording! Press O to stop capturing hand gesture.', (0, 100), font, 1, (0,255,255), 2, cv2.LINE_AA)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = hands.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if results.multi_hand_landmarks:
            hands_keypoint = []
            if len(results.multi_handedness) == 2:
                for hand in results.multi_hand_landmarks:
                    mp_draw.draw_landmarks(image, hand, mp_hands.HAND_CONNECTIONS)
                    hand = convert_landmark_list(hand)
                    hands_keypoint += hand
                if (results.multi_handedness[0].classification[0].label != results.multi_handedness[1].classification[0].label):
                    if (results.multi_handedness[0].classification[0].label == 'Right'):
                        slice = int(len(hands_keypoint) / 2)
                        hands_keypoint = hands_keypoint[slice:] + hands_keypoint[:slice]
                    logging_cv(number, mode, hands_keypoint, len(hand_signals))

            else:
                for side in results.multi_handedness:
                    if side.classification[0].label == 'Left':
                        for hand in results.multi_hand_landmarks:
                            mp_draw.draw_landmarks(image, hand, mp_hands.HAND_CONNECTIONS)
                            hand = convert_landmark_list(hand)
                            hands_keypoint += hand
                        hands_keypoint += [0.0] * 63
                        logging_cv(number, mode, hands_keypoint, len(hand_signals))
                    else:
                        hands_keypoint += [0.0] * 63
                        for hand in results.multi_hand_landmarks:
                            mp_draw.draw_landmarks(image, hand, mp_hands.HAND_CONNECTIONS)
                            hand = convert_landmark_list(hand)
                            hands_keypoint += hand
                        logging_cv(number, mode, hands_keypoint, len(hand_signals))

        cv2.imshow('Hand Tracking', image)
                
    cap.release()
    cv2.destroyAllWindows()

def select_signals(key, number, mode, signals_length):
    if 48 <= key <= signals_length + 47:
        number = key - 48
    if key == 73 or key == 105:
        mode = 1
    if key == 79 or key == 111:
        mode = 0
    return number, mode

def convert_landmark_list (hand):
    converted = []
    for landmark in hand.landmark:
        converted.append(landmark.x)
        converted.append(landmark.y)
        converted.append(landmark.z)
    return converted

def logging_cv(number, mode, hand, signals_length):
    if mode == 0:
        pass
    elif mode == 1 and (0 <= number <= signals_length - 1):
        csv_path = 'Models/KeyPoint/keypoint.csv'
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            hand.insert(0, number)
            writer.writerow(hand)
        
    return

if __name__ == "__main__":
    main()
