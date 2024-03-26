# This Python file uses the following encoding: utf-8

from dataclasses import dataclass
import threading
import logging
from PySide6.QtCore import QObject, Qt, Signal

from services.dds_service import builtin_observer
from utils import singleton

from cyclonedds.builtin import DcpsEndpoint, DcpsParticipant


@singleton
class DdsData(QObject):

    # domain observer threads
    running = []
    observer_threads = []

    # signals and slots
    new_topic_signal = Signal(int, str)
    remove_topic_signal = Signal(int, str)
    new_domain_signal = Signal(int)
    
    # data store
    domains = []
    endpoints = {}
    participants = {}

    def set_running(self, running):
        self.running = running

    def join_observer(self):
        for obs in self.observer_threads:
            obs.join()

    def add_domain(self, domain_id: int):
        if domain_id in self.domains:
            return

        self.domains.append(domain_id)
        obs_thread = threading.Thread(target=builtin_observer, args=(domain_id, self, self.running))
        obs_thread.start()
        self.observer_threads.append(obs_thread)
        self.new_domain_signal.emit(domain_id)

    def add_domain_participant(self, domain_id: int, participant: DcpsParticipant):
        logging.info(f"Add domain participant {str(participant.key)}")
        if domain_id in self.participants.keys():
            self.participants[domain_id].append(participant)
        else:
            self.participants[domain_id] = [participant]

            # TODO: emit new participant

    def remove_domain_participant(self, domain_id: int, participant: DcpsParticipant):
        if domain_id in self.participants.keys():
            available = -1
            for idx, participant_iter in enumerate(self.participants[domain_id]):
                if participant.key == participant_iter.key:
                    available = idx
                    break

            if available != -1:
                logging.info(f"Remove domain participant {str(participant.key)}")
                del self.participants[domain_id][idx]

            # TODO: emit participant gone

    def add_endpoint(self, domain_id: int, endpoint: DcpsEndpoint):
        logging.info(f"Add endpoint {str(endpoint.key)}")
        if domain_id in self.endpoints.keys():
            self.endpoints[domain_id].append(endpoint)
        else:
            self.endpoints[domain_id] = [endpoint]

        if domain_id in self.endpoints.keys():
            already_endpoint_on_topic = False
            for endpoint_iter in self.endpoints[domain_id]:
                if endpoint.topic_name == endpoint_iter.topic_name and endpoint.key != endpoint_iter.key:
                    already_endpoint_on_topic = True
                    break
    
            if not already_endpoint_on_topic:
                logging.info(f"New topic {str(endpoint.topic_name)}")
                self.new_topic_signal.emit(domain_id, endpoint.topic_name)

    def remove_endpoint(self, domain_id, endpoint: DcpsEndpoint):
        endpoint.topic_name
        if domain_id in self.endpoints.keys():
            available = -1
            other_endpoint_on_topic = False
            topic_name = ""
            for idx, endpoint_iter in enumerate(self.endpoints[domain_id]):
                if endpoint.key == endpoint_iter.key:
                    available = idx
                    topic_name = endpoint_iter.topic_name
                    break
            if available != -1:
                logging.info(f"Remove endpoint {str(endpoint.key)}")
                del self.endpoints[domain_id][idx]

            # check if it was the last endpoint on its topic
            for endpoint_iter in self.endpoints[domain_id]:
                if topic_name == endpoint_iter.topic_name:
                    other_endpoint_on_topic = True
                    break
            if not other_endpoint_on_topic:
                logging.info(f"Remove topic {str(topic_name)}")
                self.remove_topic_signal.emit(domain_id, topic_name)
