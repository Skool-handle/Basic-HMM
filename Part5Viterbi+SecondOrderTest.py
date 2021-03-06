import sys
import Part5FeatureObtainer
from Part2 import EmissionMLE
from Part3a import TransitionEstimator
from Part4a import SecondOrderTransitionEstimator


class Viterbi2(object):

    def __init__(self, transition_class, estimation_class, second_order_class,
                 forward_dict, backward_dict):
        self.transition = transition_class
        # access tag_dict for the probabilities from KEY to VALUES IN DICT
        self.estimation = estimation_class
        self.getWordProb = self.estimation.conditional_get_all_probability
        self.mid_tags_list = []  # tags that appear in the middle. i.e not start or stop.
        self.second_order = second_order_class
        for present_key in self.transition.tag_dict.keys():
            if present_key != "START" and present_key != "STOP":
                self.mid_tags_list.append(present_key)  # if it isn't START or STOP, append it.
        self.foreword = forward_dict
        self.afterword = backward_dict
        self.unkusecount = 0
        # takes in a word argument

    def get_reverse_transition_probabilities(self, destination_tag):
        # Grab all probabilities to travel to the destination tag from OTHER tags.
        return_dict = {}
        for key in self.transition.tag_dict.keys():
            try:
                return_dict[key] = self.transition.tag_dict[key][destination_tag]
            except KeyError:  # in other words if that key never heads to destination tag,
                return_dict[key] = 0
        return return_dict

    def process_sentence(self, sentence_list):
        counter = 1
        allnodes = {0: {"START":   {"CURRENT_PROB": 1, "PREV_PROB": (1, "FALSE TAG")}}}
        # False tag is there so that we don't attempt to use second order if we haven't gotten to
        # third word.
        # OuterKey -> Sequence Number
        # Inner key-> TAG NAME
        # VALUE -> {"CURRENT_PROB": current probability of this node. "PREV_PROB": (PROB,TAG)}
        # essentially, every step that you EVER took is now stored in a tuple.
        for under_consideration in range(len(sentence_list)):
            provided_word = sentence_list[under_consideration]
            if under_consideration-1 < 0:
                wordbefore = None
            else:
                wordbefore = sentence_list[under_consideration-1]
            if under_consideration+1 == len(sentence_list):
                wordafter = None
            else:
                wordafter = sentence_list[under_consideration-1]
            allnodes[counter] = self.predict(provided_word, allnodes[counter-1],
                                             wordbefore, wordafter)
            counter += 1
        # print(allnodes)
        # for sequence in allnodes.keys():
        #     print(sequence)
        #     print(allnodes[sequence])

        best_probability = 0
        best_source = (1, "ERROR")
        return_probabilities = {}
        for node in allnodes[counter - 1].keys():
            last_last_node = allnodes[counter-1][node]["PREV_PROB"][1]
            last_probability = allnodes[counter - 1][node]["CURRENT_PROB"]
            if last_last_node in self.second_order.tag_dict.keys():  # it's a real tag.
                if node in self.second_order.tag_dict[last_last_node].keys():
                    stop_transition_probabilities = \
                        self.second_order.tag_dict[last_last_node][node]["STOP"]
                else:
                    stop_transition_probabilities = 0
            else:
                stop_transition_probabilities = 0

            calculated_probability = last_probability \
                * stop_transition_probabilities
            if calculated_probability:
                best_probability = calculated_probability
                best_source = (last_probability, node)
        return_probabilities["CURRENT_PROB"] = \
            best_probability
        # save the appropriate probability.
        return_probabilities["PREV_PROB"] = best_source

        allnodes[counter] = {"STOP": return_probabilities}
        # for key in allnodes:
        #     print(key)
        #     print(allnodes[key])
        give_back_value = []
        resultant = allnodes[counter]["STOP"]["PREV_PROB"][1]
        if resultant == "ERROR":  # All previous nodes were zero...
            resultant = max(allnodes[counter-1].keys(),
                            key=(lambda k: allnodes[counter-1][k]["PREV_PROB"][1]))
            give_back_value.append(resultant)

        for z in range(counter-1, 0, -1):
            resultant = allnodes[z][resultant]["PREV_PROB"][1]
            if resultant == '':  # All nodes are ending in zero...
                resultant = max(allnodes[z].keys(),
                                key=(lambda k: allnodes[z][k]["PREV_PROB"][1]))
            give_back_value.append(resultant)
        # print(give_back_value)

        give_back_value.pop()
        give_back_value.reverse()
        return give_back_value

    def predict(self, latest_word, all_last_nodes, wordbefore, wordafter):
        # {"START":   {"CURRENT_PROB": 1, "PREV_PROB": (1, "START")}}
        # Takes in all nodes. Takes in the previous probabilities.
        # OUTER KEY -> LAST TAG
        # INNER KEYS - CURRENT PROB: current key's probability
        #            - JOURNEY: list of tuples containing the last probability
        word_to_tag_probabilities = self.getWordProb(latest_word)
        return_probabilities = {}
        forewordemitter = {}
        beforewordemitter = {}
        do_crf = True
        if wordbefore:
            if wordbefore not in self.foreword.keys():
                forewordemitter = self.foreword["#UNK#"]
                self.unkusecount += 1
            else:
                forewordemitter = self.foreword[wordbefore]
        else:  # it's the first word of a sentence...
            do_crf = False  # you can't do that here.

        if wordafter:
            if wordbefore not in self.afterword.keys():
                beforewordemitter = self.afterword["#UNK#"]
                self.unkusecount += 1
            else:
                beforewordemitter = self.afterword[wordafter]
        else:  # it's the first word of a sentence...
            # you can't CRF here!
            do_crf = False

        for some_target_tag in self.mid_tags_list:
            transition_probabilities = self.get_reverse_transition_probabilities(some_target_tag)
            # grabbed the probability to get to the target node from ALL OTHER NODES.
            this_word_probability = word_to_tag_probabilities[some_target_tag]
            best_probability = 0
            best_source = (0, "")
            # i.e if there is nothing to go from, you take it as it has an impossible combination
            for last_node in all_last_nodes.keys():
                last_probability = all_last_nodes[last_node]["CURRENT_PROB"]
                # last node's probability
                last_last_node = all_last_nodes[last_node]["PREV_PROB"][1]
                transition_to_target = transition_probabilities[last_node]
                # find second order probability.

                if last_last_node in self.second_order.tag_dict.keys():  # it's a real tag.
                    if last_node in self.second_order.tag_dict[last_last_node].keys():

                        transition_to_target = \
                            self.second_order.tag_dict[last_last_node][last_node][some_target_tag]

                if last_probability == 0 or transition_to_target == 0:
                    continue
                calculated_probability = last_probability * transition_to_target
                if do_crf:
                    calculated_probability = calculated_probability *\
                                             forewordemitter[some_target_tag] *\
                                             beforewordemitter[some_target_tag]
                # based off last probability and the one before it.

                if calculated_probability >= best_probability:
                    best_probability = calculated_probability
                    best_source = (last_probability, last_node)

            return_probabilities[some_target_tag] = {}
            return_probabilities[some_target_tag]["CURRENT_PROB"] = \
                best_probability * this_word_probability
            # save the appropriate probability.

            return_probabilities[some_target_tag]["PREV_PROB"] = best_source
            # append current node's probability
            # Grab last node tag, and probability
            # print("END")
        # print("\n\n\n\n\n\n\n\n")
        return return_probabilities


# sys.argv = ["", "EN"]
if len(sys.argv) < 2:
    print("Usage: python3 Part<>.py 'DATASET directory'")
    sys.exit()

sentence_get = Part5FeatureObtainer.file_parser(sys.argv[1]+"/train", True)
forward_dist, backward_dist, list_o_tags = \
    Part5FeatureObtainer.context_window_one_mle_own_word_distinction(sentence_get)

# Part5FeatureObtainer.converter(forward_dist)
# Part5FeatureObtainer.converter(backward_dist)
smoothed_backward = Part5FeatureObtainer.add_unk_TAG_TOTAL1(backward_dist, list_o_tags)
smoothed_forward = Part5FeatureObtainer.add_unk_TAG_TOTAL1(forward_dist, list_o_tags)
smoothed_forward = Part5FeatureObtainer.add_one_smoother_converter(smoothed_forward, list_o_tags)
smoothed_backward = Part5FeatureObtainer.add_one_smoother_converter(smoothed_backward, list_o_tags)

# prepared the additional considerations.

f = open(sys.argv[1] + "/train", "r", encoding="utf-8")
transitions = TransitionEstimator()
transitions.train(f)
f.close()
f = open(sys.argv[1] + "/train", "r", encoding="utf-8")
estimator = EmissionMLE()
estimator.train(f)
f.close()
f = open(sys.argv[1] + "/train", "r", encoding="utf-8")
secondorder = SecondOrderTransitionEstimator()
secondorder.train(f)
predictor = Viterbi2(transitions, estimator, secondorder, smoothed_forward, smoothed_backward)

input_file = open(sys.argv[1] + "/dev.in", "r", encoding="utf-8")
output_file = open(sys.argv[1] + "/dev.p5.out", "w", encoding="utf-8")

holder = []
for line in input_file.readlines():
    if line == "\n":
        return_value = predictor.process_sentence(holder)
        for i in range(len(return_value)):
            output_file.write(holder[i] + " " + return_value[i]+"\n")
        output_file.write("\n")
        holder = []
    else:
        holder.append(line[:-1])

# print(predictor.process_sentence(["Polling", "ends", "in", "Bihar", "today", ",", "counting", "on", "November", "24", "http://toi.in/ujtwya"]))
# print(predictor.process_sentence(["@yoopergirl89", "Yeah", "it", "was", "a", "long", "week", "here", "too", ".", "Luckily", "for", "me", "next", "is", "only", "Monday", "__AND__", "Tuesday", "week", "."]))
print(sys.argv[1]+" UNKNOWN USE COUNT")
print(predictor.unkusecount)
