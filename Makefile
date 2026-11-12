# Copyright 2026 Simon Emms <simon@simonemms.com>
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

SHELL := /bin/bash

cruft-update:
ifeq (,$(wildcard .cruft.json))
	@echo "Cruft not configured"
else
	@cruft check || cruft update --skip-apply-ask --refresh-private-variables
endif
.PHONY: cruft-update

check-stock:
	temporal workflow execute \
	--namespace inventory \
	--type CheckStockWorkflow \
	--task-queue Inventory \
	--input '{"sku":"WIDGET-1"}'
.PHONY: check-stock

new-order:
	@order_id="order-$${RANDOM}"; \
	temporal workflow execute \
		--namespace orders \
		--type OrderWorkflow \
		--task-queue Orders \
		--workflow-id "$$order_id" \
		--input "{\"orderId\":\"$$order_id\",\"customerRef\":\"customer-001\",\"sku\":\"WIDGET-1\",\"quantity\":2}"
.PHONY: new-order
