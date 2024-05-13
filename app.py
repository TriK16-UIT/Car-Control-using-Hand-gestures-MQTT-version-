import mediapipe as mp
import cv2
import csv
import pickle

def main():
    Trimodel = pickle.load(open('model', 'rb'))
    hand_signals = ['FW', 'ST', 'RL', 'RR', 'BW']
    font = cv2.FONT_HERSHEY_SIMPLEX
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands = 2, min_detection_confidence = 0.8, min_tracking_confidence = 0.5)
    mp_draw = mp.solutions.drawing_utils
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    while cap.isOpened(): 
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        if not ret:
            continue
        key = cv2.waitKey(10)
        if (key == 27):
            break
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = hands.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        result = None
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
                if (len(hands_keypoint) != 126):
                    continue
                result = Trimodel.predict([hands_keypoint])
                cv2.putText(image, 'Current hand signal: {} - {}'.format(str(result[0]), str(hand_signals[result[0]])), (0, 200), font, 1, (0,255,255), 2, cv2.LINE_AA)
            else:
                for side in results.multi_handedness:
                    if side.classification[0].label == 'Left':
                        for hand in results.multi_hand_landmarks:
                            mp_draw.draw_landmarks(image, hand, mp_hands.HAND_CONNECTIONS)
                            hand = convert_landmark_list(hand)
                            hands_keypoint += hand
                        hands_keypoint += [0.0] * 63
                    else:
                        hands_keypoint += [0.0] * 63
                        for hand in results.multi_hand_landmarks:
                            mp_draw.draw_landmarks(image, hand, mp_hands.HAND_CONNECTIONS)
                            hand = convert_landmark_list(hand)
                            hands_keypoint += hand
                if (len(hands_keypoint) != 126):
                    continue
                result = Trimodel.predict([hands_keypoint])
                cv2.putText(image, 'Current hand signal: {} - {}'.format(str(result[0]), str(hand_signals[result[0]])), (0, 200), font, 1, (0,255,255), 2, cv2.LINE_AA)
        cv2.imshow('Hand Tracking', image)
    cap.release()
    cv2.destroyAllWindows()

def convert_landmark_list (hand):
    converted = []
    for landmark in hand.landmark:
        converted.append(landmark.x)
        converted.append(landmark.y)
        converted.append(landmark.z)
    return converted

if __name__ == "__main__":
    main()