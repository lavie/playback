from enum import Enum
import logging

_logger = logging.getLogger(__name__)


EqualityStatus = Enum('EqualityStatus', 'Equal Different')


class ComparatorResult(object):
    def __init__(self, equality_status, message=None, diff=None):
        """
        :param equality_status: Equality status between expected and actual
        :type equality_status: EqualityStatus
        :param message: Optional comparison message
        :type message: basestring
        """
        self.equality_status = equality_status
        self.message = message
        self.diff = diff

    def __str__(self):
        if not self.message:
            return u'{}'.format(self.equality_status.name)

        return u'{} - {}'.format(self.equality_status.name, self.message)


class Comparison(object):
    def __init__(self, comparator_result, expected, actual, expected_is_exception, actual_is_exception, playback):
        """
        :param comparator_result: Result of comparison between expected and actual
        :type comparator_result: ComparatorResult
        :param expected: Expected result (recording)
        :type expected: Any
        :param actual: Actual result (playback)
        :type actual: Any
        :param expected_is_exception: Is expected result an exception (recording)
        :type expected_is_exception: bool
        :param actual_is_exception: Is actual result an exception (recording)
        :type actual_is_exception: bool
        :param playback: Play operation result
        :type playback: playback.tape_recorder.Playback
        """
        self.comparator_status = comparator_result
        self.expected = expected
        self.actual = actual
        self.expected_is_exception = expected_is_exception
        self.actual_is_exception = actual_is_exception
        self.playback = playback

    def __str__(self):
        result = self.comparator_status.equality_status.name
        if self.comparator_status.message:
            result += u' - ' + self.comparator_status.message
        return result


class Equalizer(object):
    def __init__(self, playable_recordings, result_extractor, comparator,
                 comparison_data_extractor=None):
        """
        :param playable_recordings: Iterator of playable recordings to compare
        :type playable_recordings:
        collections.Iterator[playback.comparison.recordings_lookup.PlayableRecording]
        :param result_extractor: Extracts result from the recording and playback
        :type result_extractor: function
        :param comparison_data_extractor: Extracts optional data from the recording that will be passed to the
        comparator
        :type comparison_data_extractor: function
        :param comparator: A function use to create the equality status by comparing the expected vs actual result
        :type comparator: function
        """
        self.playable_recordings = playable_recordings
        self.result_extractor = result_extractor
        self.comparison_data_extractor = comparison_data_extractor
        self.comparator = comparator

    def run_comparison(self):
        """
        Runs a comparison between recorded results and their corresponding playbacks
        :return: Comparison result
        :rtype: list of Comparison
        """
        comparisons = []
        equal = 0
        diff = 0
        failure = 0
        iteration = 0
        for iteration, playable_recording in enumerate(self.playable_recordings, start=1):
            try:
                playback = playable_recording.play()
                recorded_result = self.result_extractor(playback.recorded_outputs)
                playback_result = self.result_extractor(playback.playback_outputs)

                comparison_data = {} if self.comparison_data_extractor is None else \
                    self.comparison_data_extractor(playback.original_recording)

                comparator_result = self.comparator(recorded_result, playback_result, **comparison_data)
                if not isinstance(comparator_result, ComparatorResult):
                    comparator_result = ComparatorResult(comparator_result)

                comparison = Comparison(
                    comparator_result,
                    recorded_result,
                    playback_result,
                    expected_is_exception=isinstance(recorded_result, Exception),
                    actual_is_exception=isinstance(playback_result, Exception),
                    playback=playback
                )

                _logger.info(u'Recording {} Comparison result: {}'.format(playable_recording.recording_id, comparison))

                if comparison.comparator_status.equality_status is EqualityStatus.Equal:
                    equal += 1
                else:
                    diff += 1

                if iteration % 10 == 0:
                    _logger.info(u'Iteration {} stats: equal - {}, different - {}, failure - {}'.format(
                        iteration, equal, diff, failure))

                comparisons.append(comparison)
            except Exception as ex:
                failure += 1
                _logger.info(u'Failed playing recording id {} - {}'.format(playable_recording.recording_id, ex))

        _logger.info(u'Completed all {} iterations, stats: equal - {}, different - {}, failure - {}'.format(
            iteration, equal, diff, failure))
        return comparisons