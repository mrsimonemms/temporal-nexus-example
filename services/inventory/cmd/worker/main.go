/*
 * Copyright 2026 Simon Emms <simon@simonemms.com>
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package main

import (
	"context"
	"os"

	gh "github.com/mrsimonemms/golang-helpers"
	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app"
	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/activities"
	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/inventory"
	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/service"
	"github.com/mrsimonemms/temporal-nexus/example/services/inventory/internal/app/workflows"
	"github.com/rs/zerolog/log"
	temporal "github.com/zigflow/helpers"
	"go.temporal.io/sdk/contrib/sysinfo"
	"go.temporal.io/sdk/worker"
)

func exec() error {
	c, err := temporal.NewConnectionWithEnvvars(
		temporal.WithZerolog(&log.Logger),
	)
	if err != nil {
		return gh.FatalError{
			Cause: err,
			Msg:   "Error creating Temporal connection",
		}
	}
	defer c.Close()

	w := worker.New(c, app.TaskQueue, worker.Options{
		SysInfoProvider: sysinfo.SysInfoProvider(),
	})

	ctx := context.Background()

	log.Debug().Msg("Registering workflows")
	w.RegisterWorkflow(workflows.CheckStockWorkflow)
	w.RegisterWorkflow(workflows.AllocateStockWorkflow)

	// In-memory stock shared by all Activities in this process. It resets on
	// restart and requires a single Inventory worker.
	store := inventory.NewStore(inventory.SeedStock)
	log.Info().Interface("stock", inventory.SeedStock).Msg("Inventory: seeded in-memory stock")

	acts, err := activities.NewActivities(store)
	if err != nil {
		return gh.FatalError{
			Cause: err,
			Msg:   "Unable to create activities",
		}
	}

	log.Debug().Msg("Registering activities")
	w.RegisterActivity(acts)

	log.Debug().Msg("Registering Nexus service")
	svc, err := service.New()
	if err != nil {
		return gh.FatalError{
			Cause: err,
			Msg:   "Unable to create Nexus service",
		}
	}
	w.RegisterNexusService(svc)

	log.Debug().Msg("Starting health check server")
	if err := temporal.NewHealthCheck(ctx, []string{app.TaskQueue}, "localhost:3000", c); err != nil {
		return gh.FatalError{
			Cause: err,
			Msg:   "Error starting health check",
		}
	}

	if err := w.Run(worker.InterruptCh()); err != nil {
		return gh.FatalError{
			Cause: err,
			Msg:   "Workflow stopped",
		}
	}

	return nil
}

func main() {
	if err := exec(); err != nil {
		os.Exit(gh.HandleFatalError(err))
	}
}
