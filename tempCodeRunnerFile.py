else:
                for side in results.multi_handedness:
                    if side.classification[0].label == 'Left':
                        for hand in results.multi_hand_landmarks:
                            hand = convert_landmark_list(hand)
                            hands_keypoint += hand
                        hands_keypoint += [0.0] * 63
                    else:
                        hands_keypoint += [0.0] * 63
                        for hand in results.multi_hand_landmarks:
                            hand = convert_landmark_list(hand)
                            hands_keypoint += hand
                result = Trimodel.predict([hands_keypoint])