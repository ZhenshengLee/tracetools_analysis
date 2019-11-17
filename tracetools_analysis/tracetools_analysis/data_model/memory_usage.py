# Copyright 2019 Apex.AI, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for memory usage data model."""

import pandas as pd

from . import DataModel


class MemoryUsageDataModel(DataModel):
    """
    Container to model pre-processed memory usage data for analysis.

    Contains changes in memory allocation (e.g. + for malloc, - for free) with the corresponding
    timestamp.
    """

    def __init__(self) -> None:
        """Create a MemoryUsageDataModel."""
        super().__init__()
        self.memory_diff = pd.DataFrame(columns=[
            'timestamp',
            'tid',
            'memory_diff',
        ])

    def add_memory_difference(
        self,
        timestamp: int,
        tid: int,
        memory_diff: int,
    ) -> None:
        data = {
            'timestamp': timestamp,
            'tid': tid,
            'memory_diff': memory_diff,
        }
        self.memory_diff = self.memory_diff.append(data, ignore_index=True)

    def print_data(self) -> None:
        print('==================MEMORY USAGE DATA MODEL==================')
        tail = 20
        print(f'Memory difference (tail={tail}):\n{self.times.tail(tail).to_string()}')
        print('===========================================================')
