from __future__ import annotations
import os, asyncio, json
import urllib.parse
import issutilities.actions as do
import discord, discord.utils as utils
from discord.ext import commands, tasks
from rapidfuzz import process as rfp
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    import objects
    from issutilities.client import HTTP as client

name = (os.path.basename(__file__)).replace(".py", "")

class Cache:
    def __init__(self) -> None:
        self.CurrentWarID: int | None
        self.WarStatus: HD2.Schemas.WarStatus
        self.WarInfo: HD2.Schemas.WarInfo
        self.NewsFeed: HD2.Schemas.NewsFeed
        self.MajorOrders: HD2.Schemas.MajorOrders
        self.WarTime: HD2.Schemas.WarTime
        self.WarStats: HD2.Schemas.WarStats
        self.Leaderboard: HD2.Schemas.Leaderboard
        
        self.GameClientConfiguration: HD2.Schemas.GameClientConfiguration

        self.cached_health: dict[int, int | float | None] = {}

        self.ready: bool = False

    def remap(self) -> None:
        WI = self.WarInfo
        WSU = self.WarStatus
        WS = self.WarStats
        MO = self.MajorOrders

        # Mapped to WarStatus
        for planet_status in WSU.planet_status:
            planet_status.current_faction = next(faction for faction in WI.factions if faction.id == planet_status.raw_current_faction)
            planet_status.planet = next(planet for planet in WI.planets if planet.id == planet_status.raw_planet)

            for attr, val in planet_status.__dict__.items():
                if attr not in ["raw_planet", "planet"]:
                    setattr(planet_status.planet, attr, val)
        
        for planet_attack in WSU.planet_attacks:
            planet_attack.source = next(planet for planet in WI.planets if planet.id == planet_attack.raw_source)
            planet_attack.target = next(planet for planet in WI.planets if planet.id == planet_attack.raw_target)
        
        for campaign in WSU.campaigns:
            campaign.planet = next(planet for planet in WI.planets if planet.id == campaign.raw_planet)
        
        for joint_operation in WSU.joint_operations:
            joint_operation.planet = next(planet for planet in WI.planets if planet.id == joint_operation.raw_planet)
        
        for planet_event in WSU.planet_events:
            planet_event.planet = next(planet for planet in WI.planets if planet.id == planet_event.raw_planet)
            planet_event.faction = next(faction for faction in WI.factions if faction.id == planet_event.raw_faction)
            planet_event.campaign = next(campaign for campaign in WSU.campaigns if campaign.id == planet_event.raw_campaign)
            planet_event.joint_operations = [joint_operation for joint_operation in WSU.joint_operations if joint_operation.id in planet_event.raw_joint_operations]
        
        for global_event in WSU.global_events:
            global_event.planets = [planet for planet in WI.planets if planet.id in global_event.raw_planets]
            global_event.sectors = [sector for sector in WI.sectors if any(map(lambda v: v in sector.raw_planets, [pl.id for pl in global_event.planets]))]
            global_event.faction = next(faction for faction in WI.factions if faction.id == global_event.raw_faction)
        
        # Mapped to WarInfo
        __temp_home_world_mapping = dict.fromkeys([faction.id for faction in WI.factions], [])

        for planet in WI.planets:
            planet.waypoints = [o_planet for o_planet in WI.planets if planet.id in planet.raw_waypoints]
            planet.sector = next(sector for sector in WI.sectors if planet.id in sector.raw_planets)
            planet.initial_faction = next(faction for faction in WI.factions if faction.id == planet.raw_initial_faction)
            planet.status = next(planet_status for planet_status in WSU.planet_status if planet.id == planet_status.raw_planet)
            planet.conflicts = {
                "to": [atk for atk in WSU.planet_attacks if atk.raw_source == planet.id],
                "from": [_def for _def in WSU.planet_attacks if _def.raw_target == planet.id]
            }
            planet.attacks = planet.conflicts
            planet.involved_campaigns = [campaign for campaign in WSU.campaigns if planet.id == campaign.raw_planet]
            planet.playable = len(planet.involved_campaigns) > 0
            planet.involved_joint_operations = [joint_op for joint_op in WSU.joint_operations if planet.id == joint_operation.raw_planet]
            planet.events = [event for event in WSU.planet_events if event.raw_planet == planet.id]
            planet.involved_global_events = [gevent for gevent in WSU.global_events if planet.id in gevent.raw_planets]
            
            for home_world_payload in WI.raw_home_worlds:
                pi: list[int] = home_world_payload.get("planetIndices", [])
                fi = home_world_payload.get("race", 0)

                if planet.id in pi:
                    planet.home_world_of = next(faction for faction in WI.factions if fi == faction.id)
                    break
            else:
                planet.home_world_of = None
            
            planet.stats = next((pstats for pstats in WS.planet_stats if pstats.raw_planet == planet.id), HD2.Objects.PlanetStats({"planetIndex": planet.id}))

            planet.status.liberation = 1 - (planet.status.current_health / planet.max_health)

            if planet.home_world_of:
                __temp_home_world_mapping[planet.home_world_of.id].append(planet)
        
        for fi, ps in __temp_home_world_mapping.items():
            WI.home_worlds.append({"faction": next((f for f in WI.factions if f.id == fi)), "planets": ps})

        del __temp_home_world_mapping

        for faction in WI.factions:
            faction.current_planets = [planet for planet in WI.planets if planet.status.raw_current_faction == faction.id]
            faction.initial_planets = [planet for planet in WI.planets if planet.raw_initial_faction == faction.id]
            faction.home_worlds = [planet for planet in WI.planets if planet.home_world_of and planet.home_world_of.id == faction.id]
            faction.sectors = [sector for sector in WI.sectors if any(map(lambda v: v in sector.raw_planets, [pl.id for pl in faction.current_planets]))]

        for sector in WI.sectors:
            sector.planets = [planet for planet in WI.planets if planet.id in sector.raw_planets]
            sector.raw_faction = list(set([planet.status.raw_current_faction for planet in WI.planets]))
            sector.faction = next(faction for faction in WI.factions if faction.id == sector.raw_faction[0]) if len(sector.raw_faction) == 1 else HD2.Objects.ContestedSectorFaction(sector, [faction for faction in WI.factions if faction.id in sector.raw_faction])
            if isinstance(sector.faction, HD2.Objects.ContestedSectorFaction):
                WI.contested_factions.append(sector.faction)

        # Mapped to WarStats
        for planet_stat in WS.planet_stats:
            planet_stat.planet = next(planet for planet in WI.planets if planet.id == planet_stat.raw_planet)

        for order in MO.orders:
            for task in order.tasks:
                task.target_faction = next(faction for faction in WI.factions if faction.id == task.raw_target_faction)
                task.target_planet = next((planet for planet in WI.planets if planet.id == task.raw_target_planet), None)

        self.ready = True

    def recalculate_lib_estimate(self, time_delta: float | int) -> None:
        # figure out how to calculate a defense mission

        for planet in self.WarInfo.planets:
            if not getattr(planet, "status", None):
                continue

            current_health = planet.status.current_health
            max_health = planet.max_health
            planet.status.liberation = 1-(current_health/max_health)

            if not (cached_health := self.cached_health.get(planet.id)):
                self.cached_health[planet.id] = current_health
                continue

            raw_delta = (current_health - cached_health)
            raw_rate = raw_delta/time_delta

            planet.status.raw_rate = raw_rate
            planet.status.net_rate = (raw_delta/max_health)/time_delta
            planet.status.rate = planet.status.net_rate + planet.status.regen_per_hour

            try:
                finish_timedelta = timedelta(seconds=(planet.max_health - planet.status.current_health)/raw_rate)
                planet.status.estimated_liberation_time = utils.utcnow() + finish_timedelta
            except:
                planet.status.estimated_liberation_time = None

class HD2:
    class Schemas:
        # Parsed from Endpoints.WarStatus
        class WarStatus:
            def __init__(self, war_status_payload: dict[str, Any]) -> None:
                # war_id (int): The War that the status belongs to.
                self.war_id: int = war_status_payload.get("warId", 0)

                # elapsed_time (int): The elapsed time of this war. Due to server issues, this is usually unreliable.
                self.elapsed_time: int = war_status_payload.get("time", 0)

                # start_time (datetime): The calculated start time. Due to mAny factors, this is unreliable and only an estimate.
                self.start_time: datetime = utils.utcnow() - timedelta(seconds=self.elapsed_time)

                # impact_multiplier (float): The multiplier inversely based on total player count. Affects how much liberation is done to planets.
                self.impact_multiplier: float = war_status_payload.get("impactMultiplier", 0.0)

                # story_beat_id_32 (int): The id of the status's "story beat". Current usage is unknown.
                self.story_beat_id_32: int = war_status_payload.get("storyBeatId32", 0)

                # planet_status (list[PlanetStatus]): A list of planet statuses. Also accessible via Planet.status.
                self.planet_status: list[HD2.Objects.PlanetStatus] = [
                    HD2.Objects.PlanetStatus(planet_status_payload)
                    for planet_status_payload in war_status_payload.get("planetStatus", [])
                ]

                # planet_attacks (list[PlanetAttack]): A list of planet attacks. Also accessible via Planet.attacks.
                self.planet_attacks: list[HD2.Objects.PlanetAttack] = [
                    HD2.Objects.PlanetAttack(planet_attack_payload)
                    for planet_attack_payload in war_status_payload.get("planetAttacks", [])
                ]

                # campaigns (list[WarCampaign]): A list of war campaigns. Also accessible via Planet.involved_campaigns.
                self.campaigns: list[HD2.Objects.WarCampaign] = [
                    HD2.Objects.WarCampaign(war_campaign_payload)
                    for war_campaign_payload in war_status_payload.get("campaigns", [])
                ]

                # community_targets (list[CommunityTarget]): A list of community targets. Currently unused.
                self.community_targets: list[HD2.Objects.CommunityTarget] = [
                    HD2.Objects.CommunityTarget(community_target_payload)
                    for community_target_payload in war_status_payload.get(
                        "communityTargets", []
                    )
                ]

                # joint_operations (list[JointOperation]): A list of joint operations. Also accessible via Planet.involved_joint_operations. Usage is unknown.
                self.joint_operations: list[HD2.Objects.JointOperation] = [
                    HD2.Objects.JointOperation(joint_operation_payload)
                    for joint_operation_payload in war_status_payload.get(
                        "jointOperations", []
                    )
                ]

                # planet_events (list[PlanetEvent]): A list of planet events. Also accessible via Planet.events.
                self.planet_events: list[HD2.Objects.PlanetEvent] = [
                    HD2.Objects.PlanetEvent(planet_event_payload)
                    for planet_event_payload in war_status_payload.get("planetEvents", [])
                ]

                # planet_active_effects (list[PlanetActiveEffect]): A list of active planet effects. Also accessible via Planet.active_effects. Currently unused.
                self.planet_active_effects: list[HD2.Objects.PlanetActiveEffect] = [
                    HD2.Objects.PlanetActiveEffect(planet_active_effect_payload)
                    for planet_active_effect_payload in war_status_payload.get(
                        "planetActiveEffects", []
                    )
                ]

                # active_election_policy_effects (list[ActiveElectionPolicyEffects]): A list of active election policy effects. Currently unused.
                self.active_election_policy_effects: list[HD2.Objects.ActiveElectionPolicyEffect] = [
                    HD2.Objects.ActiveElectionPolicyEffect(active_election_policy_effect_payload)
                    for active_election_policy_effect_payload in war_status_payload.get(
                        "activeElectionPolicyEffects", []
                    )
                ]

                # global_events (list[GlobalEvent]): A list of global events. Also accessible via Planet.involved_global_events.
                self.global_events: list[HD2.Objects.GlobalEvent] = [
                    HD2.Objects.GlobalEvent(global_event_payload)
                    for global_event_payload in war_status_payload.get("globalEvents", [])
                ]

                # super_earth_war_results (SuperEarthWarResult): The results of a presumed war on/around Super Earth. Currently unused.
                self.super_earth_war_results: HD2.Objects.SuperEarthWarResult = HD2.Objects.SuperEarthWarResult(
                    war_status_payload.get("superEarthWarResults", [])
                )

        # Parsed from Endpoints.WarInfo
        class WarInfo:
            def __init__(self, war_info_payload: dict[str, Any]) -> None:
                # war_id (int): The War that the info belongs to.
                self.war_id: int = war_info_payload.get("warId", 0)

                # start_date (datetime): The date in which this war started.
                self.start_date: datetime = datetime.fromtimestamp(
                    war_info_payload.get("startDate", utils.utcnow().timestamp())
                )

                # end_date (datetime): The date in which this war will end/ended at.
                self.end_date: datetime = datetime.fromtimestamp(
                    war_info_payload.get("endDate", utils.utcnow().timestamp())
                )

                # minimum_client_version (str): The client version required for a player to play in this war.
                self.minimum_client_version: str = war_info_payload.get(
                    "minimumClientVersion", "0.0.1"
                )

                # planets (list[Planet]): A list of all planets in the game.
                self.planets: list[HD2.Objects.Planet] = [
                    HD2.Objects.Planet(planet_payload)
                    for planet_payload in war_info_payload.get("planetInfos", [])
                ]

                # sectors (list[Sector]): A list of sectors in the game.
                self.sectors: list[HD2.Objects.Sector] = [HD2.Objects.Sector(sector_name) for sector_name in HD2.Mappings.Sectors.keys()]

                # factions (list[Faction]): A list of factions in the game. Does not include "contested sector factions".
                self.factions: list[HD2.Objects.Faction] = [HD2.Objects.Faction(faction_index) for faction_index in HD2.Mappings.Factions.keys() if type(faction_index) == int]

                # contested_factions (list[ContestedSectorFaction]): A list of factions that represent a sector being contested by two other factions.
                self.contested_factions: list[HD2.Objects.ContestedSectorFaction] = []

                # raw_home_worlds (list[dict[str, Any]]): A list of home world planet indices by faction.
                self.raw_home_worlds: list[dict[str, Any]] = war_info_payload.get("homeWorlds", [])

                # capitals (list[Capital]): A list of capitals. Currently unused.
                self.capitals: list[HD2.Objects.Capital] = [
                    HD2.Objects.Capital(capital_payload)
                    for capital_payload in war_info_payload.get("capitals", [])
                ]

                # planet_permanent_effects (list[PlanetPermanentEffect]): A list of permanent planet effects. Also accessible via Planet.permanent_effects. Currently unused.
                self.planet_permanent_effects: list[HD2.Objects.PlanetPermanentEffect] = [
                    HD2.Objects.PlanetPermanentEffect(planet_permanent_effect_payload)
                    for planet_permanent_effect_payload in war_info_payload.get(
                        "planetPermanentEffects", []
                    )
                ]

                # home_worlds (list[dict[str, Faction | list[Planet]]]): All homeworlds of every faction.
                self.home_worlds: list[dict[str, HD2.Objects.Faction | list[HD2.Objects.Planet]]] = []

        # Parsed from Endpoints.NewsFeed
        class NewsFeed:
            def __init__(self, news_feed_payload: list[dict[str, Any]]) -> None:
                # posts (list[NewsPost]): A list of news posts.
                self.posts: list[HD2.Objects.NewsPost] = [
                    HD2.Objects.NewsPost(news_post_payload)
                    for news_post_payload in news_feed_payload
                ]

        # Parsed from Endpoints.MajorOrders
        class MajorOrders:
            def __init__(
                self, major_orders_payload: list[dict[str, Any]]
            ) -> None:
                # orders (list[MajorOrder]): A list of ongoing major orders.
                self.orders: list[HD2.Objects.MajorOrder] = [
                    HD2.Objects.MajorOrder(major_order_payload)
                    for major_order_payload in major_orders_payload
                ]

        # Parsed from Endpoints.WarTime and Endpoints.TimeSinceStart
        class WarTime:
            def __init__(
                self,
                combined_payload: dict[str, dict[str, int]]
            ) -> None:
                war_time_payload: dict[str, int] = combined_payload.get("WarTime", {})
                time_since_start_payload: dict[str, int] = combined_payload.get("TimeSinceStart", {})

                # elapsed_war_time (int): The amount of seconds since the war season began. Generally unreliable due to server issues.
                self.elapsed_war_time: int = war_time_payload.get("time", 0)

                # time_since_start (int): The amount of seconds since the start of the API.
                self.time_since_start: int = time_since_start_payload.get("secondsSinceStart", 0)

        # Parsed from Endpoints.WarStats
        class WarStats:
            def __init__(self, war_stats_payload: dict[str, Any]) -> None:
                # galaxy_stats (GalaxyStats): Statistics about the galactic war.
                self.galaxy_stats: HD2.Objects.GalaxyStats = HD2.Objects.GalaxyStats(
                    war_stats_payload.get("galaxy_stats", {})
                )

                # planet_stats (list[PlanetStats]): A list of statistics for each planet, if available.
                self.planet_stats: list[HD2.Objects.PlanetStats] = [
                    HD2.Objects.PlanetStats(planet_stats_payload)
                    for planet_stats_payload in war_stats_payload.get("planet_stats", [])
                ]

        # Parsed from Endpoints.Leaderboard
        class Leaderboard:
            def __init__(self, leaderboard_payload: dict[str, Any]) -> None:
                # page_number (int): The page number queried.
                self.page_number: int = leaderboard_payload.get("pageNumber", 0)

                # page_size (int): The amount of entries per page.
                self.page_size: int = leaderboard_payload.get("pageSize", 10)

                # total_records (int): The amount of values in the leaderboard. Effectively a count of people of who've played the game.
                self.total_records: int = leaderboard_payload.get("totalRecords", 0)

                # entries (list[LeaderboardEntry]): A list of leaderboard entries. The amount and rankings will vary based on page number and page size.
                self.entries: list[HD2.Objects.LeaderboardEntry] = [HD2.Objects.LeaderboardEntry(leaderboard_entry_payload) for leaderboard_entry_payload in leaderboard_payload.get("entries", [])]
    
        # Parsed from Endpoints.GameClientConfiguration
        class GameClientConfiguration:
            def __init__(self, game_client_configuration: dict[str, Any]) -> None:
                # polling_configuration (list[PollingConfiguration]): A list of polling settings.
                self.polling_configuration: list[HD2.Objects.PollingConfiguration] = [HD2.Objects.PollingConfiguration(polling_configuration_payload) for polling_configuration_payload in game_client_configuration.get("pollingConfiguration", [])]

                # feature_configuration (list[FeatureConfiguration]): A list of settings for features.
                self.feature_configuration: list[HD2.Objects.FeatureConfiguration] = [HD2.Objects.FeatureConfiguration(feature_configuration_payload) for feature_configuration_payload in game_client_configuration.get("featureConfiguration", [])]

                # matchmaking_configuration (dict[str, MatchmakingConfiguration]): Settings of matchmaking attributes, mapped to each attribute.
                self.matchmaking_configuration = {name: HD2.Objects.MatchmakingConfiguration(match_making_configuration_payload) for name, match_making_configuration_payload in game_client_configuration.get("matchmakingConfiguration", [])}

    class Objects:
        # For Endpoints.Status
        class PlanetStatus:
            def __init__(self, planet_status_payload: dict[str, Any]) -> None:
                # raw_planet (int): The index of the planet this status belongs to.
                self.raw_planet: int = planet_status_payload.get("index", 0)

                # raw_current_faction (int): The mapping index of the current faction that controls this planet.
                self.raw_current_faction: int = planet_status_payload.get("owner", 0)

                # current_health (int): The current health of the planet, in terms of liberation.
                self.current_health: int = planet_status_payload.get("health", 1_000_000)

                # regen_per_second (float): The current health regen rate per second.
                self.regen_per_second: float = planet_status_payload.get("regenPerSecond", 0.0)

                # regen_per_minute (float): The calculated health regen rate per minute.
                self.regen_per_minute: float = self.regen_per_second * 60.0

                # regen_per_hour (float): The calculated health regen rate per hour.
                self.regen_per_hour: float = self.regen_per_second * 3600.0

                # players (int): The amount of players currently on the planet.
                self.players: int = planet_status_payload.get("players", 0)

                # current_faction (Faction): The faction that currently controls this planet.
                self.current_faction: HD2.Objects.Faction

                # planet (Planet): The planet that this status belongs to.
                self.planet: HD2.Objects.Planet

                # rate (float): The current rate of liberation change, per hour. Defaults to 0 if not enough data was collected.
                self.rate: float = 0.0

                # net_rate (float): The net rate of liberation change, per hour. Defaults to 0 if not enough data was collected.
                self.net_rate: float = 0.0

                # raw_rate (float | None): The raw health that is removed from planets, per hour. Defaults to 0 if not enough data was collected.
                self.raw_rate: float = 0.0

                # liberation (float): The liberation percentage as represented by a float between 0.0 and 1.0.
                self.liberation: float = 0.0

                # estimated_liberation_time (datetime | None): The time at which planet liberation will occur. Could be None if it's too far in time.
                self.estimated_liberation_time: datetime | None = None

        class PlanetAttack:
            def __init__(self, planet_attack_payload: dict[str, int]) -> None:
                # raw_source (int): The index of the planet where the attack is coming from.
                self.raw_source: int = planet_attack_payload.get("source", 0)

                # raw_target (int): The index of the planet where the attack is directed at.
                self.raw_target: int = planet_attack_payload.get("target", 260)

                # source (Planet): The planet where the attack is coming from.
                self.source: HD2.Objects.Planet

                # target (Planet): The planet where the attack is directed at.
                self.target: HD2.Objects.Planet

        class WarCampaign:
            def __init__(self, war_campaign_payload: dict[str, int]) -> None:
                # id (int): The ID of the campaign.
                self.id: int = war_campaign_payload.get("id", 0)

                # raw_planet (int): The index of the planet that this campaign involves.
                self.raw_planet: int = war_campaign_payload.get("planetIndex", 0)

                # type (str): The campaign type for this campaign.
                self.type: str | dict[bool, str] = HD2.Types.WarCampaign.get(
                    (raw_type := war_campaign_payload.get("type", 0)),
                    f"Campaign Type {raw_type}",
                )

                # count (int): Speculated to be how mAny times the campaign has been played.
                self.count: int = war_campaign_payload.get("count", 0)

                # planet (Planet): The planet that this campaign involves.
                self.planet: HD2.Objects.Planet

        class CommunityTarget: # NEEDS MAPPING
            def __init__(self, community_target_payload: Any) -> None:
                pass

        class JointOperation:
            def __init__(
                self, joint_operation_payload: dict[str, int]
            ) -> None:
                # id (int): The id for this joint operation.
                self.id: int = joint_operation_payload.get("id", 0)

                # raw_planet (int): The index of the planet this joint operation belongs to.
                self.raw_planet: int = joint_operation_payload.get("planetIndex", 0)

                # hq_node_index (int): Internal value. Usage unknown.
                self.hq_node_index: int = joint_operation_payload.get("hqNodeIndex", 0)

                # planet (Planet): The planet this joint operation belongs to.
                self.planet: HD2.Objects.Planet

        class PlanetEvent:
            def __init__(self, planet_event_payload: dict[str, Any]) -> None:
                # id (int): The id for this planet event.
                self.id: int = planet_event_payload.get("id", 0)

                # raw_planet (int): The index of the planet this event belongs to.
                self.raw_planet: int = planet_event_payload.get("planetIndex", 0)

                # type (str): The event type for this event.
                self.type: str = HD2.Types.PlanetEvent.get(
                    (raw_type := planet_event_payload.get("eventType", 0)), str(raw_type)
                )

                # raw_faction (int): The index of the faction that is involved in this event.
                self.raw_faction: int = planet_event_payload.get("race", 0)

                # event_health (int): The current health of the involved planet. This only applies for the event.
                self.event_health: int = planet_event_payload.get("health", 1_000_000)

                # event_max_health (int): The maximum health of the involved planet. This only applies for the event.
                self.event_max_health: int = planet_event_payload.get("maxHealth", 1_000_000)

                # elapsed_start_time (int): The amount of seconds since the start of the war (WarTime) when this event starts/started.
                self.elapsed_start_time: int = planet_event_payload.get("startTime", 0)

                # elapsed_end_time (int): The amount of seconds since the start of the war (WarTime) when this event ends/ended.
                self.elapsed_end_time: int = planet_event_payload.get("expireTime", 0)

                # raw_campaign (int): The id of the campaign this event is a part of.
                self.raw_campaign: int = planet_event_payload.get("campaignId", 0)

                # raw_joint_operations (list[int]): A list of ids of joint operations that involve this event.
                self.raw_joint_operations: list[int] = planet_event_payload.get("jointOperationIds", [])

                # planet (Planet): The planet that this event belongs to.
                self.planet: HD2.Objects.Planet

                # faction (Faction): The faction that is involved in this event.
                self.faction: HD2.Objects.Faction

                # campaign (Campaign): The campaign this event is a part of.
                self.campaign: HD2.Objects.WarCampaign

                # joint_operations (list[JointOperation]): A list of joint operations that involve this event.
                self.joint_operations: list[HD2.Objects.JointOperation]

        class PlanetActiveEffect: # NEEDS MAPPING
            def __init__(self, planet_active_effect_payload: Any) -> None:
                pass

        class Capital: # NEEDS MAPPING
            def __init__(self, capital_payload: Any) -> None:
                pass

        class PlanetPermanentEffect: # NEEDS MAPPING
            def __init__(self, planet_permanent_effect_payload: Any) -> None:
                pass

        class ActiveElectionPolicyEffect: # NEEDS MAPPING
            def __init__(
                self, active_election_policy_effect_payload: Any
            ) -> None:
                pass

        class GlobalEvent:
            def __init__(self, global_event_payload: dict[str, Any]) -> None:
                # id (int): The id for this event.
                self.id: int = global_event_payload.get("eventId", 0)

                # id_32 (int): Internal id. Usage unknown.
                self.id_32: int = global_event_payload.get("id32", 0)

                # portrait_id_32 (int): Internal id. Usage unknown.
                self.portrait_id_32: int = global_event_payload.get("portraitId32", 0)

                # title (str): The title of the event.
                self.title: str = global_event_payload.get("title", "EVENT")

                # title_id_32 (int): The id of the title. Usage unknown.
                self.title_id_32: int = global_event_payload.get("titleId32", 0)

                # description (str): The description of the event.
                # message (str): ALias of description.
                self.description: str = global_event_payload.get("message", "")
                self.message = self.description

                # message_id_32 (int): The id of the description of the event. Usage unknown.
                self.message_id_32: int = global_event_payload.get("messageId32", 0)

                # raw_faction (int): The index of the faction that this event applies to.
                self.raw_faction: int = global_event_payload.get("race", 0)

                # flag (int): Internal flag. Mapping and usage unknown.
                self.flag: int = HD2.Types.GlobalEventFlag.get((raw_flag := global_event_payload.get("flag", 0)), raw_flag)

                # assignment_id_32 (int): Internal value. Mapping and usage unknown.
                self.assignment_id_32: int = global_event_payload.get("assignmentId32", 0)

                # raw_effects (list[int]): A list of effect ids.
                self.raw_effects: list[int] = global_event_payload.get("efffectIds", [])

                # effects (list[GlobalEffect]): Currently an alias of raw_effects until these are mapped.
                self.effects: list[int] = self.raw_effects

                # raw_planets (list[int]): A list of indices for planets involved in this event.
                self.raw_planets: list[int] = global_event_payload.get("planetIndices", [])

                # planets (list[Planet]): A list of planets involved in this event.
                self.planets: list[HD2.Objects.Planet]

                # sectors (list[Sector]): A list of sectors that are involved in this event.
                self.sectors: list[HD2.Objects.Sector]

                # faction (Faction): The faction that this event applies to.
                self.faction: HD2.Objects.Faction

        class SuperEarthWarResult: # NEEDS MAPPING
            def __init__(
                self, super_earth_war_result_payload: Any
            ) -> None:
                pass

        # For Endpoints.WarInfo
        class Planet:
            def __init__(self, planet_payload: dict[str, Any]) -> None:
                # index (int): The index of the planet.
                # id (int): Alias of index.
                self.index: int = planet_payload.get("index", 0)
                self.id = self.index

                # name (str): The name of the planet.
                self.name: str = HD2.Mappings.Planets.get(self.id, "Planet")

                # settings_hash (int): Internal value. Usage is unknown.
                self.settings_hash: int = planet_payload.get("settingsHash", 0)

                # position (PlanetPosition): The relative position of the planet to origin (0, 0) as decimals in the range [-1, 1].
                self.position: HD2.Objects.PlanetPosition = HD2.Objects.PlanetPosition(planet_payload.get("position", {}))

                # raw_waypoints (list[int]): A list of indices of planets accessible via this planet.
                self.raw_waypoints: list[int] = planet_payload.get("waypoints", [])

                # raw_sector (int): The index of the sector that this planet is in, as provided by the API. This has been known to be inaccurate and is suggested to be unused.
                self.raw_sector: int = planet_payload.get("sector", 0)

                # max_health (int): The maximum health the planet has normally.
                self.max_health: int = planet_payload.get("maxHealth", 1_000_000)

                # disabled (bool): Whether or not the planet has been forcibly disabled by the game master. This is not indicative of playability; use playable instead.
                self.disabled: bool = planet_payload.get("disabled", False)

                # raw_initial_faction (int): The index of the faction that initially controlled this planet.
                self.raw_initial_faction: int = planet_payload.get("initialOwner", 0)

                # waypoints (list[Planet]): A list of planets accessible via this planet.
                self.waypoints: list[HD2.Objects.Planet]

                # sector (Sector): The sector that the planet is in.
                self.sector: HD2.Objects.Sector

                # initial_faction (Faction): The faction that initially controlled this planet.
                self.initial_faction: HD2.Objects.Faction

                # playable (bool): Whether or not the planet is playable.
                self.playable: bool = False

                # status (PlanetStatus): The status of the planet.
                self.status: HD2.Objects.PlanetStatus

                # conflicts (dict[str, list[PlanetAttack]]): Attacks to/from other planets.
                # attacks (dict[str, list[PlanetAttack]]): Alias to conflicts.
                self.conflicts: dict[str, list[HD2.Objects.PlanetAttack]]
                self.attacks: dict[str, list[HD2.Objects.PlanetAttack]]

                # involved_campaigns (list[Campaign]): A list of campaigns that involve this planet.
                self.involved_campaigns: list[HD2.Objects.WarCampaign]

                # involved_joint_operations (list[JointOperation]): A list of joint operations that involve this planet.
                self.involved_joint_operations: list[HD2.Objects.JointOperation]

                # events (list[PlanetEvent]): A list of events occurring on this planet.
                self.events: list[HD2.Objects.PlanetEvent]

                # active_effects (list[PlanetActiveEffect]): A list of active effects on this planet.
                self.active_effects: list[HD2.Objects.PlanetActiveEffect]

                # involved_global_events (list[GlobalEvent]): A list of global events that involve this planet.
                self.involved_global_events: list[HD2.Objects.GlobalEvent]

                # home_world_of (Faction | None): The faction this planet is a home world of, if Any.
                self.home_world_of: HD2.Objects.Faction | None

                # permanent_effects (list[PlanetPermanentEffect]): A list of permanent effects that apply to this planet.
                self.permanent_effects: list[HD2.Objects.PlanetPermanentEffect]

                # stats (PlanetStats): The stats for this planet.
                self.stats: HD2.Objects.PlanetStats
  
        class PlanetPosition:
            def __init__(self, planet_position_payload: dict[str, float]) -> None:
                # x (float): The x-coordinate of the planet, relative to the origin 0.
                self.x: float = planet_position_payload.get("x", 0.0)

                # y (float): The x-coordinate of the planet, relative to the origin 0.
                self.y: float = planet_position_payload.get("y", 0.0)

                # dict (dict[str, float]): The coordinates in original dict form.
                self.dict: dict[str, float] = planet_position_payload

        class Sector:
            def __init__(
                self, sector_name: str
            ) -> None:
                # name (str): The name of sector.
                self.name: str = sector_name or "Unknown"

                self.__raw_mapping_payload: dict[str, Any] = HD2.Mappings.Sectors.get(self.name, {})

                # index (int): The index of the sector. This has been mapped as best as possible from the API, but due to inconsistencies this is unreliable.
                # id (int): Alias of index.
                self.index: int = self.__raw_mapping_payload.get("index", 0)
                self.id = self.index

                # raw_planets (list[int]): A list of indices of planets in this sector.
                self.raw_planets: list[int] = self.__raw_mapping_payload.get("planets", [])

                # raw_faction (list[int]): A list of faction indices that currently control this sector. This does not signify if the sector is contested.
                self.raw_faction: list[int]

                # planets (list[Planet]): A list of planets in this sector.
                self.planets: list[HD2.Objects.Planet]

                # faction (Faction | ContestedSectorFaction): The faction that currently controls this sector. If multiple factions are present, a "Contested" faction is returned instead.
                self.faction: HD2.Objects.Faction | HD2.Objects.ContestedSectorFaction

        class BaseFaction:
            def __init__(self, faction_index: int | str) -> None:
                # index (int | str): The index of the mapping that this faction correlates to.
                # id (int | str): Alias of index.
                self.index: int | str = faction_index
                self.id = self.index

                self.__raw_mapping_payload: dict[str, str] = HD2.Mappings.Factions.get(self.id, {})

                # name (str): The name of the faction.
                self.name: str = self.__raw_mapping_payload.get("name", "Unknown")

                # icon (str): The icon/emoji that represents this faction. May change to be an image later on.
                # emoji (str): Alias for icon. May replace icon soon.
                self.icon: str = self.__raw_mapping_payload.get("emoji", "❓")
                self.emoji = self.icon

        class Faction(BaseFaction):
            def __init__(
                self,
                faction_index: int,
            ) -> None:
                super().__init__(faction_index)

                # current_planets (list[Planet]): A list of planets under control by this faction.
                # planets (list[Planet]): Alias for current_planets.
                self.current_planets: list[HD2.Objects.Planet]

                # initial_planets (list[Planet] | None): A list of planets that were under control of this faction at the start of the war.
                self.initial_planets: list[HD2.Objects.Planet]

                # home_worlds (list[Planet]): A list of planets that are home worlds to the faction.
                self.home_worlds: list[HD2.Objects.Planet]

                # sectors (list[Sector]): A list of sectors under control by this faction.
                self.sectors: list[HD2.Objects.Sector]

        class ContestedSectorFaction(BaseFaction):
            def __init__(self, sector: HD2.Objects.Sector, factions_involved: list[HD2.Objects.Faction]) -> None:
                super().__init__("C")

                # contesters (list[Faction]: A list of factions involved in the contested sector.
                self.contesters: list[HD2.Objects.Faction] = factions_involved

                # home_worlds (list[dict[str, Faction | list[Planet]]]): The lists of home worlds mapped to each faction involved.
                self.home_worlds: list[dict[str, HD2.Objects.Faction | list[HD2.Objects.Planet]]] = [{"faction": faction, "planets": faction.home_worlds} for faction in self.contesters]

                # sector (Sector): The sector involved.
                # sectors (Sector): To keep consistency with Faction, this is an alias to sector.
                self.sector: HD2.Objects.Sector = sector
                self.sectors = self.sector

                # planets (list[Planet]]): A list of planets in this sector.
                # current_planets (list[Planet]): To keep consistency with Faction, this is an alias to planets.
                # initial_planets (list[Planet]): To keep consistency with Faction, this is an alias to planets.
                self.planets: list[HD2.Objects.Planet] = self.sector.planets
                self.current_planets = self.planets

        # For Endpoints.NewsFeed
        class NewsPost:
            def __init__(self, news_post_payload: dict[str, Any]) -> None:
                # id (int): The id of the news post.
                self.id: int = news_post_payload.get("id", 0)

                # elapsed_published (int): The amount of seconds since the start of the war (WarTime) when this post was published.
                self.elapsed_published: int = news_post_payload.get("published", 0)

                # type (str): The post type for this post.
                self.type: str = HD2.Types.NewsPost.get(
                    (raw_type := news_post_payload.get("type", 0)), str(raw_type)
                )

                # tag_ids (list[Any]): A list of tag IDs. Currently unused.
                self.tag_ids: list[Any] = news_post_payload.get("tagIds", [])

                # message (str): The message content of this post. May contain an all-capitalized title on the first line.
                self.message: str = news_post_payload.get(
                    "message", "SOMETHING HAPPENED\nThe message was lost, however!"
                )

        # For Endpoints.MajorOrder
        class MajorOrder:
            def __init__(self, major_order_payload: dict[str, Any]) -> None:
                self.__raw_content: dict[str, Any]  = major_order_payload.get("setting", {})
                self.__raw_progress: list[int] = major_order_payload.get("progress", [])

                # id (int): The id of the major order.
                # id_32 (int): Alias of id.
                self.id: int = major_order_payload.get("id32", 0)
                self.id_32 = self.id

                # expires_in (int): The amount of seconds left in this major order.
                self.expires_in: int = major_order_payload.get("expiresIn", 0)

                # expires_at (datetime): The time in which this major order expires at.
                self.expires_at: datetime = datetime.fromtimestamp(utils.utcnow().timestamp() + self.expires_in)

                # type (str): The order type for this major order.
                self.type: str = HD2.Types.MajorOrder.get(
                    (raw_type := self.__raw_content.get("type", 0)), str(raw_type)
                )

                # title (str): The title of the major order.
                self.title: str = self.__raw_content.get("overrideTitle", "MAJOR ORDER")

                # message (str): The message content of the major order.
                self.message = self.__raw_content.get(
                    "overrideBrief", "There is an ongoing major order."
                )

                # task_title (str): The title of the task.
                self.task_title: str = self.__raw_content.get(
                    "taskDescription", "Spread Democracy."
                )

                # reward (MajorOrderReward): The reward for successfully completing the major order.
                self.reward: HD2.Objects.MajorOrderReward = HD2.Objects.MajorOrderReward(self.__raw_content.get("reward", {}))

                # flags (int): An unknown value.
                self.flags: Any = self.__raw_content.get("flags")

                # tasks (list[MajorOrderTask]): A list of tasks for the major order.
                self.tasks: list[HD2.Objects.MajorOrderTask] = [HD2.Objects.MajorOrderTask(major_order_task_payload) for major_order_task_payload in self.__raw_content.get("tasks", {})]

                __current_progress = sum(self.__raw_progress)
                __max_progress = sum([task.total_count for task in self.tasks])

                # progress (float): The overall percentage (represented as a decimal) of completion of this major order. For specific progress, check each task.
                self.progress: float = __current_progress/__max_progress
            
        class MajorOrderTask:
            def __init__(
                self, major_order_task_payload: dict[str, Any]
            ) -> None:
                # type (str): The type of major order task this is.
                self.type: str = HD2.Types.MajorOrderTask.get(major_order_task_payload.get("type", 0), "Unknown")

                # raw_target_faction (int): The index of the faction that this task is targeted at.
                self.raw_target_faction: int

                # total_count (int): The total count/progress of this task (i.e., this value would be 2,000,000,000 for a "kill 2 billion terminids" task.)
                self.total_count: int

                # target_faction (Faction): The faction that this task is targetd at.
                self.target_faction: HD2.Objects.Faction

                # liberation_needed (bool): Whether or not there is liberation required in this task.
                self.liberation_needed: bool

                # raw_target_planet (int):  The index of the planet that this task is targeted at.
                self.raw_target_planet: int

                # target_planet (Planet): The planet that this task is targeted at. If None, this means that multiple/no planets are targeted.
                self.target_planet: HD2.Objects.Planet | None

                # unknowns (dict[int, Any]): A mapping of unknown values.
                self.unknowns: dict[int, Any]

                self.resolve_task_types(major_order_task_payload.get("values", []), major_order_task_payload.get("valueTypes", []))

            def resolve_task_types(self, values: list[int], value_types: list[int]) -> None:
                unknowns = {}
                for (value, value_type) in zip(values, value_types):
                    real_type = HD2.Types.MajorOrderTaskValue.get(value_type, None)

                    if not real_type:
                        unknowns[value_type] = value
                        continue

                    setattr(self, f"raw_{real_type}", value)

                self.total_count = getattr(self, "raw_total_count", 1)
                self.liberation_needed = bool(getattr(self, "raw_liberation_needed", None))
                self.unknowns = unknowns
                    
        class MajorOrderReward:
            def __init__(
                self, major_order_reward_payload: dict[str, int]
            ) -> None:
                # type (str): The type of reward, usually currency of some sort.
                # name (str): Alias of type.
                # object (str): Alias of type.
                self.type: str = HD2.Types.MajorOrderReward.get(major_order_reward_payload.get("type", 0), "Unknown")
                self.name = self.type
                self.object = self.type

                # id (int): The id of the reward.
                self.id: int = major_order_reward_payload.get("id32", 0)

                # amount (int): The amount of the reward that will be given.
                self.amount: int = major_order_reward_payload.get("amount", 0)

                # flags (int): Value with unknown usage.
                self.flags: int = HD2.Types.MajorOrderRewardFlag.get((raw_flag := major_order_reward_payload.get("flags", 0)), raw_flag)

        # For Endpoints.WarStats
        class BaseStats:
            def __init__(self, stats_payload: dict[str, int]) -> None:
                # missions_won (int): The amount of missions that were successful (i.e. the main objectives were completed).
                self.missions_won: int = stats_payload.get("missionsWon", 1)

                # missions_lost (int): The amount of missions that failed (i.e. the main objectives were not completed).
                self.missions_lost: int = stats_payload.get("missionsLost", 0)

                # mission_time_played (int): The cumulative number of seconds of playtime spent inside of missions from all players.
                self.mission_time_played: int = stats_payload.get("missionTime", 0)

                # total_missions (int): The total amount of missions executed.
                self.total_missions: int = self.missions_won + self.missions_lost

                # mission_success_rate (int): The percentage of missions won over total missions, rounded to the tenths place and multiplied by 100. This is highly inaccurate to the true success rate.
                self.mission_success_rate: int = stats_payload.get("missionSuccessRate", 0)

                # success_rate (float): The percentage of missions won over total missions, represented as a decimal number.
                self.success_rate: float = self.missions_won / (self.total_missions if self.total_missions > 0 else 1)

                # terminid_kills (int): The amount of Terminid killed.
                # bug_kills (int): Alias for terminid_kills.
                self.terminid_kills: int = stats_payload.get("bugKills", 0)
                self.bug_kills = self.terminid_kills

                # automaton_kills (int): The amount of Automaton killed.
                # bot_kills (int): Alias for automaton_kills.
                self.automaton_kills: int = stats_payload.get("automatonKills", 0)
                self.bot_kills = self.automaton_kills

                # illuminate_kills (int): The amount of Illuminate killed.
                # droid_kills (int): Alias for illuminate_kills.
                self.illuminate_kills: int = stats_payload.get("illuminateKills", 0)
                self.droid_kills = self.illuminate_kills

                # shots_fired (int): The amount of shots that were fired.
                # bullets_fired (int): Alias for shots_fired.
                self.shots_fired: int = stats_payload.get("bulletsFired", 0)
                self.bullets_fired = self.shots_fired

                # shots_hit (int): The amount of shots that have hit characters. Includes friendly fire. Some weapons may fire more than one bullet per shot so therefore, this value may be above shots_fired.
                # bullets_hit (int): Alias for shots_hit. 
                self.shots_hit: int = stats_payload.get("bulletsHit", 0)
                self.bullets_hit = self.shots_hit

                # given_accuracy (int): The percentage of shots hitting over shots firing, rounded to the tenths place and multiplied by 100. This is highly inaccurate to the true accuracy.
                # accurracy (int): Intentionally mispelled alias of given_accuracy.
                self.raw_accuracy: int = stats_payload.get("accurracy", 0)
                self.accurracy = self.raw_accuracy

                # accuracy (float): The percentage of shots hitting over shots firing, represented as a decimal.
                self.accuracy: float = self.shots_hit / (self.shots_fired if self.shots_fired > 0 else 1)

                # time_played (int): The cumulative number of seconds of playtime from all players.
                self.time_played: int = stats_payload.get("timePlayed", 0)

                # mission_time_proportion (float): The percentage of time that was spent inside of missions.
                self.mission_time_proportion: float = self.mission_time_played / (self.time_played if self.time_played > 0 else 1)

                # deaths (int): The total number of helldiver deaths.
                self.deaths: int = stats_payload.get("deaths", 0)

                # friendly_kills (int): The number of deaths from friendly fire.
                self.friendly_kills: int = stats_payload.get("friendlies", 0)

                # friendly_fire_rate (float): The percentage of deaths that were from friendly fire.
                self.friendly_fire_rate: float = self.friendly_kills / (self.deaths if self.deaths > 0 else 1)

                # revives (int): The number of revives that were performed.
                self.revives: int = stats_payload.get("revives", 0)

        class GalaxyStats(BaseStats):
            def __init__(self, galaxy_stats_payload: dict[str, int]) -> None:
                super().__init__(galaxy_stats_payload)

        class PlanetStats(BaseStats):
            def __init__(self, planet_stats_payload: dict[str, int]) -> None:
                super().__init__(planet_stats_payload)

                # raw_planet (int): The index of the planet that these stats belong to.
                self.raw_planet: int = planet_stats_payload.get("planetIndex", 0)

                # planet (Planet): The planet that these stats belong to.
                self.planet: HD2.Objects.Planet

        # For Endpoints.Leaderboard
        class LeaderboardEntry:
            SUFFIXES = {1: "st", 2: "nd", 3: "rd"}

            def __init__(self, leaderboard_entry_payload: dict[str, Any]) -> None:
                # rank (int): The rank of the player.
                # placement (int): Alias to rank.
                self.rank: int = leaderboard_entry_payload.get("rank", 0)
                self.placement = self.rank

                # ranking (str): Similar to rank, but with a generated suffix.
                # placed (str): Alias to ranking.
                self.ranking: str = self.__generate_ranking(self.rank)
                self.placed = self.ranking

                # experience (int): How much experience this player has. Speculated to be only for the current level.
                # exp (int): Alias for experience.
                # xp (int): Alias for experieence.
                self.experience: int = leaderboard_entry_payload.get("experience", 0)
                self.exp = self.experience
                self.xp = self.experience

                # banner (int): Speculated to be a reference to in-game banners. Current usage is still unknown.
                self.banner: int = leaderboard_entry_payload.get("banner", 0)

                # name (str): The name of the player.
                # username (str): Alias to name.
                self.name: str = leaderboard_entry_payload.get("name", "Unknown")
                self.username = self.name

                # is_self (bool): Whether or not the player is you. Because there is no authentication procedure at the moment, this will always be false.
                self.is_self: Literal[False] = leaderboard_entry_payload.get("isSelf", False) # bool

                # score (int): The score of the player. Calculation for score is unknown.
                # points (int): Alias for score.
                self.score: int = leaderboard_entry_payload.get("score", 0)
                self.points = self.score

            @classmethod
            def __generate_ranking(cls, placement: int) -> str:
                if type(placement) != int:
                    return str(placement)
                
                suffix = cls.SUFFIXES.get(abs(placement) % 10, "th") if abs(placement) % 100 not in [11, 12, 13] else "th"
                
                return f"{placement}{suffix}"
    
        # For Endpoints.GameClientConfiguration
        class PollingConfiguration:
            def __init__(self, polling_configuration_payload: dict[str, int]) -> None:
                # id_32 (int): The internal id of the value to poll.
                self.id_32: int = polling_configuration_payload.get("id32", 0)

                # interval (int): The amount of seconds to wait after polling the value.
                self.interval: int = polling_configuration_payload.get("interval", 60)

        class FeatureConfiguration:
            def __init__(self, feature_configuration: dict[str, int | bool]) -> None:
                # id_32 (int): The internal id of the feature.
                self.id_32: int = feature_configuration.get("id32", 0)

                # enabled (bool): Whether or not the feature is enabled.
                self.enabled = feature_configuration.get("enabled", True)

        class MatchmakingConfiguration:
            def __init__(self, match_making_configuration_payload: list[dict[str, int]]) -> None:
                # values (list[MatchmakingConfigValue]): A list of values for the configuration.
                self.values = [HD2.Objects.MatchmakingConfigValue(match_making_config_value_payload) for match_making_config_value_payload in match_making_configuration_payload]

        class MatchmakingConfigValue:
            def __init__(self, match_making_config_value_payload: dict[str, int]) -> None:
                # weight (int): Unknown value.
                self.weight = match_making_config_value_payload.get("weight", 1)
                
                # value (int): Unknown value.
                self.value = match_making_config_value_payload.get("value", 0)

    class Endpoints:
        def __init__(self) -> None:
            ## Private/Setup Vars
            # API Links
            self.__api_official = os.getenv("HELLDIVERS_API")
            self.__api_official_v2 = f"{self.__api_official}/v2"
            self.__api_diveharder = "https://api.diveharder.com/raw"

            # Raw Season Endpoints
            self.__raw_warseason = f"{self.__api_official}/WarSeason"
            self.__raw_newsfeed = f"{self.__api_official}/NewsFeed"
            self.__raw_assignment = f"{self.__api_official_v2}/Assignment/War"
            self.__raw_stats = f"{self.__api_official}/Stats/War"
            self.__raw_leaderboard = {
                "main": f"{self.__api_official}/Leaderboard/HotF/v2/Player",
                "params": ["PageNumber", "PageSize"],
            }

            ## Public Vars
            self.CurrentWarID = f"{self.__raw_warseason}/Current/WarID"
            self.GameClientConfiguration = f"{self.__api_official}/Configuration/GameClient"

            # Other (have not looked into)
            self.NewsTicker = f"{self.__api_diveharder}/NewsTicker"
            self.GalacticWarEffects = f"{self.__api_diveharder}/GalacticWarEffects"
            self.LevelSpec = f"{self.__api_diveharder}/LevelSpec"
            self.Items = f"{self.__api_diveharder}/Items"
            self.MissionRewards = f"{self.__api_diveharder}/MissionRewards"

        ## Helper
        def set_season_endpoints(self, war_id: int | None = 801) -> None:
            ## Private/Setup Vars
            self.__warseason = f"{self.__raw_warseason}/{war_id}"

            ## Public Vars
            self.WarStatus = f"{self.__warseason}/Status"
            self.WarInfo = f"{self.__warseason}/WarInfo"
            self.NewsFeed = f"{self.__raw_newsfeed}/{war_id}"
            self.MajorOrders = f"{self.__raw_assignment}/{war_id}"
            self.WarTime = f"{self.__warseason}/WarTime"
            self.TimeSinceStart = f"{self.__warseason}/TimeSinceStart"
            self.WarStats = f"{self.__raw_stats}/{war_id}/Summary"
            self.Leaderboard = {"main": f"{self.__raw_leaderboard.get("main")}/{war_id}", "params": self.__raw_leaderboard.get("params")}

        ## Utils
        def make_query_url(self, url: str, params: dict[str, str]) -> str:
            raw_combined_url = "?".join(
                [
                    url,
                    "&".join(
                        [f"{param}={value}" for param, value in list(params.items())]
                    ),
                ]
            )
            return urllib.parse.quote(raw_combined_url)
    
    class Mappings:
        Planets = {
            0: "Super Earth",
            1: "Klen Dahth II",
            2: "Pathfinder V",
            3: "Widow's Harbor",
            4: "New Haven",
            5: "Pilen V",
            6: "Hydrofall Prime",
            7: "Zea Rugosia",
            8: "Darrowsport",
            9: "Fornskogur II",
            10: "Midasburg",
            11: "Cerberus IIIc",
            12: "Prosperity Falls",
            13: "Okul VI",
            14: "Martyr's Bay",
            15: "Freedom Peak",
            16: "Fort Union",
            17: "Kelvinor",
            18: "Wraith",
            19: "Igla",
            20: "New Kiruna",
            21: "Fort Justice",
            22: "Zegema Paradise",
            23: "Providence",
            24: "Primordia",
            25: "Sulfura",
            26: "Nublaria I",
            27: "Krakatwo",
            28: "Volterra",
            29: "Crucible",
            30: "Veil",
            31: "Marre IV",
            32: "Fort Sanctuary",
            33: "Seyshel Beach",
            34: "Hellmire",
            35: "Effluvia",
            36: "Solghast",
            37: "Diluvia",
            38: "Viridia Prime",
            39: "Obari",
            40: "Myradesh",
            41: "Atrama",
            42: "Emeria",
            43: "Barabos",
            44: "Fenmire",
            45: "Mastia",
            46: "Shallus",
            47: "Krakabos",
            48: "Iridica",
            49: "Azterra",
            50: "Azur Secundus",
            51: "Ivis",
            52: "Slif",
            53: "Caramoor",
            54: "Kharst",
            55: "Eukoria",
            56: "Myrium",
            57: "Kerth Secundus",
            58: "Parsh",
            59: "Reaf",
            60: "Irulta",
            61: "Emorath",
            62: "Ilduna Prime",
            63: "Maw",
            64: "Meridia",
            65: "Borea",
            66: "Curia",
            67: "Tarsh",
            68: "Shelt",
            69: "Imber",
            70: "Blistica",
            71: "Ratch",
            72: "Julheim",
            73: "Valgaard",
            74: "Arkturus",
            75: "Esker",
            76: "Terrek",
            77: "Cirrus",
            78: "Crimsica",
            79: "Heeth",
            80: "Veld",
            81: "Alta V",
            82: "Ursica XI",
            83: "Inari",
            84: "Skaash",
            85: "Moradesh",
            86: "Rasp",
            87: "Bashyr",
            88: "Regnus",
            89: "Mog",
            90: "Valmox",
            91: "Iro",
            92: "Grafmere",
            93: "New Stockholm",
            94: "Oasis",
            95: "Genesis Prime",
            96: "Outpost 32",
            97: "Calypso",
            98: "Elysian Meadows",
            99: "Alderidge Cove",
            100: "Trandor",
            101: "East Iridium Trading Bay",
            102: "Liberty Ridge",
            103: "Baldrick Prime",
            104: "The Weir",
            105: "Kuper",
            106: "Oslo Station",
            107: "Pöpli IX",
            108: "Gunvald",
            109: "Dolph",
            110: "Bekvam III",
            111: "Duma Tyr",
            112: "Vernen Wells",
            113: "Aesir Pass",
            114: "Aurora Bay",
            115: "Penta",
            116: "Gaellivare",
            117: "Vog-sojoth",
            118: "Kirrik",
            119: "Mortax Prime",
            120: "Wilford Station",
            121: "Pioneer II",
            122: "Erson Sands",
            123: "Socorro III",
            124: "Bore Rock",
            125: "Fenrir III",
            126: "Turing",
            127: "Angel's Venture",
            128: "Darius II",
            129: "Acamar IV",
            130: "Achernar Secundus",
            131: "Achird III",
            132: "Acrab XI",
            133: "Acrux IX",
            134: "Acubens Prime",
            135: "Adhara",
            136: "Afoyay Bay",
            137: "Ain-5",
            138: "Alairt III",
            139: "Alamak VII",
            140: "Alaraph",
            141: "Alathfar XI",
            142: "Andar",
            143: "Asperoth Prime",
            144: "Bellatrix",
            145: "Botein",
            146: "Osupsam",
            147: "Brink-2",
            148: "Bunda Secundus",
            149: "Canopus",
            150: "Caph",
            151: "Castor",
            152: "Durgen",
            153: "Draupnir",
            154: "Mort",
            155: "Ingmar",
            156: "Charbal-VII",
            157: "Charon Prime",
            158: "Choepessa IV",
            159: "Choohe",
            160: "Chort Bay",
            161: "Claorell",
            162: "Clasa",
            163: "Demiurg",
            164: "Deneb Secundus",
            165: "Electra Bay",
            166: "Enuliale",
            167: "Epsilon Phoencis VI",
            168: "Erata Prime",
            169: "Estanu",
            170: "Fori Prime",
            171: "Gacrux",
            172: "Gar Haren",
            173: "Gatria",
            174: "Gemma",
            175: "Grand Errant",
            176: "Hadar",
            177: "Haka",
            178: "Haldus",
            179: "Halies Port",
            180: "Herthon Secundus",
            181: "Hesoe Prime",
            182: "Heze Bay",
            183: "Hort",
            184: "Hydrobius",
            185: "Karlia",
            186: "Keid",
            187: "Khandark",
            188: "Klaka 5",
            189: "Kneth Port",
            190: "Kraz",
            191: "Kuma",
            192: "Lastofe",
            193: "Leng Secundus",
            194: "Lesath",
            195: "Maia",
            196: "Malevelon Creek",
            197: "Mantes",
            198: "Marfark",
            199: "Martale",
            200: "Matar Bay",
            201: "Meissa",
            202: "Mekbuda",
            203: "Menkent",
            204: "Merak",
            205: "Merga IV",
            206: "Minchir",
            207: "Mintoria",
            208: "Mordia 9",
            209: "Nabatea Secundus",
            210: "Navi VII",
            211: "Nivel 43",
            212: "Oshaune",
            213: "Overgoe Prime",
            214: "Pandion-XXIV",
            215: "Partion",
            216: "Peacock",
            217: "Phact Bay",
            218: "Pherkad Secundus",
            219: "Polaris Prime",
            220: "Pollux 31",
            221: "Prasa",
            222: "Propus",
            223: "Ras Algethi",
            224: "Rd-4",
            225: "Rogue 5",
            226: "Rirga Bay",
            227: "Seasse",
            228: "Senge 23",
            229: "Setia",
            230: "Shete",
            231: "Siemnot",
            232: "Sirius",
            233: "Skat Bay",
            234: "Spherion",
            235: "Stor Tha Prime",
            236: "Stout",
            237: "Termadon",
            238: "Tibit",
            239: "Tien Kwan",
            240: "Troost",
            241: "Ubanea",
            242: "Ustotu",
            243: "Vandalon IV",
            244: "Varylia 5",
            245: "Wasat",
            246: "Vega Bay",
            247: "Wezen",
            248: "Vindemitarix Prime",
            249: "X-45",
            250: "Yed Prior",
            251: "Zefia",
            252: "Zosma",
            253: "Zzaniah Prime",
            254: "Skitter",
            255: "Euphoria III",
            256: "Diaspora X",
            257: "Gemstone Bluffs",
            258: "Zagon Prime",
            259: "Omicron",
            260: "Cyberstan",
        }
        Sectors = {
            "Sol": {"planets": [0], "index": 0},
            "Altus": {"planets": [2, 1, 3, 4, 5], "index": 1},
            "Barnard": {"planets": [6, 8, 10, 9, 30, 31], "index": 2},
            "Cancri": {"planets": [32, 33, 35, 11, 12], "index": 3},
            "Gothmar": {"planets": [13, 36, 37], "index": 4},
            "Cantolus": {"planets": [38, 39, 15, 14, 17], "index": 5},
            "Idun": {"planets": [18, 41, 40, 63], "index": 6},
            "Kelvin": {"planets": [42, 19, 20, 21, 22], "index": 7},
            "Iptus": {"planets": [23, 24, 47, 48, 71, 73], "index": 8},
            "Celeste": {"planets": [25, 26, 27, 51, 52, 85], "index": 9},
            "Korpus": {"planets": [28, 29, 83, 53, 81], "index": 10},
            "Gallux": {"planets": [54, 87, 86, 134, 135, 136], "index": 11},
            "Morgon": {"planets": [89, 88, 55, 56], "index": 12},
            "Rictus": {"planets": [90, 91, 92, 94, 95, 57, 58], "index": 13},
            "Saleria": {"planets": [97, 96, 59, 60], "index": 14},
            "Meridian": {"planets": [61, 62, 103, 102], "index": 15},
            "Theseus": {"planets": [104, 105, 150, 151, 192, 239], "index": 16},
            "Sagan": {"planets": [65, 106, 108], "index": 17},
            "Marspira": {"planets": [43, 44, 66, 67, 45], "index": 18},
            "Talus": {"planets": [68, 46, 69, 116], "index": 19},
            "Orion": {"planets": [16, 49, 76, 77, 79, 127, 80], "index": 20},
            "Draco": {"planets": [169, 78, 170], "index": 21},
            "Umlaut": {"planets": [64, 125, 126, 168], "index": 22},
            "Borgus": {"planets": [82, 128, 131, 130], "index": 23},
            "Ursa": {"planets": [84, 132, 174, 133], "index": 24},
            "Ferris": {"planets": [7, 180, 178, 176], "index": 25},
            "Hanzo": {"planets": [93, 182, 138, 139, 137], "index": 26},
            "Akira": {"planets": [186, 143, 142, 141, 140], "index": 27},
            "Guang": {"planets": [98, 99, 144, 145, 187], "index": 28},
            "Tarragon": {"planets": [148, 149, 146, 147, 101], "index": 29},
            "Alstrad": {"planets": [190, 188, 189], "index": 30},
            "Xzar": {"planets": [107, 154, 155, 153, 197], "index": 31},
            "Nanos": {"planets": [72, 109, 110, 111], "index": 32},
            "Andromeda": {"planets": [157, 198, 199, 156, 200], "index": 33},
            "Hydra": {"planets": [112, 113, 203], "index": 34},
            "Tanis": {"planets": [117, 161, 162, 163, 250, 251], "index": 35},
            "Arturion": {"planets": [74, 119, 118, 120, 121, 165, 164], "index": 36},
            "Falstaff": {"planets": [124, 75, 122, 123], "index": 37},
            "Mirin": {"planets": [34, 211, 212, 258], "index": 38},
            "Jin_Xi": {"planets": [129, 173, 172, 217, 214, 171], "index": 39},
            "Farsight": {"planets": [175, 219, 218, 221, 220], "index": 40},
            "Leo": {"planets": [177, 179, 223, 222], "index": 41},
            "Rigel": {"planets": [181, 183, 226, 225, 224], "index": 42},
            "Omega": {"planets": [227, 185, 184, 229, 228], "index": 43},
            "Xi_Tauri": {"planets": [231, 230, 233, 232], "index": 44},
            "Quintus": {"planets": [193, 237, 236, 235, 234], "index": 45},
            "Severin": {"planets": [152, 196, 195, 241, 238], "index": 46},
            "Lacaille": {"planets": [115, 160, 159, 194], "index": 47},
            "Trigon": {"planets": [158, 240, 242, 243, 244], "index": 48},
            "Ymir": {"planets": [201, 245, 249, 246, 247], "index": 49},
            "Valdis": {"planets": [114, 202, 204, 205, 260, 248], "index": 50},
            "Gellert": {"planets": [70, 207, 206, 252, 253], "index": 51},
            "Hawking": {"planets": [191, 208, 255, 254], "index": 52},
            "L'estrade": {"planets": [166, 167, 209, 210, 256, 257, 259], "index": 53},
            "Sten": {"planets": [50, 100, 213, 216, 215], "index": 54},
        }
        Factions = {
            0: {"emoji": "❓", "name": "Unknown"},
            1: {"emoji": "<:superearth:1218539071669014538>", "name": "Human"},
            2: {"emoji": "<:terminids:1218539026974380183>", "name": "Terminid"},
            3: {"emoji": "<:automatons:1218538972012085268>", "name": "Automaton"},
            4: {"emoji": "🔺", "name": "Illuminate"},
            "C": {"emoji": "❗", "name": "Contested"},
        }

    class Types:
        WarCampaign = {0: {True: "Defense", False: "Liberation"}, 1: "Recon", 2: "Story"}
        PlanetEvent = {1: "Defense Campaign"}
        GlobalEventFlag = {}
        NewsPost = {}
        MajorOrder = {4: "Galactic War"}
        MajorOrderTask = {3: "Eradication", 11: "Liberation", 12: "Defense", 13: "Control"}
        MajorOrderTaskValue = {1: "target_faction", 3: "total_count", 11: "liberation_needed", 12: "target_planet"}
        MajorOrderReward = {1: "Medals"}
        MajorOrderRewardFlag = {}

class Converter:
    DT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    @classmethod
    def to_discord(cls, date: str | datetime | None, ts_format: utils.TimestampStyle = "R") -> str:
        date = date if date else utils.utcnow()

        def __get_date(date: str) -> datetime:
            return datetime.strptime(date, cls.DT_FORMAT)
        
        def __get_timestamp(dt: datetime) -> str:
            return utils.format_dt(dt, ts_format)
        
        try:
            return __get_timestamp(date) if type(date) == datetime else __get_timestamp(__get_date(str(date)))
        except:
            return cls.to_discord(utils.utcnow())
    
    @staticmethod
    def label(value: str, label: str | None = "Sector") -> str:
        try:
            is_num = int(value)
        except ValueError:
            is_num = False

        return f"{label} {value}" if is_num else f"{value} {label}"
        
class Utilities:
    def __init__(self, bot: objects.Bot) -> None:
        self.bot = bot

    @staticmethod
    def auto_complete(raw_query: str, iterable: list) -> tuple[str, bool]:
        query = raw_query.title()
        substrings = [
            planet for planet in iterable if query.lower() in planet.lower()
        ]

        best_match_direct = query if query in iterable else None
        best_match_substring = rfp.extractOne(query, substrings, score_cutoff=75)
        best_match_full = rfp.extractOne(query, iterable, score_cutoff=75)

        if best_match_direct:
            return best_match_direct, True

        if best_match_substring is None and best_match_full is None:
            top_3 = rfp.extract(query, substrings, limit=3)
            top_3_full = rfp.extract(query, iterable, limit=3)

            top_3.extend(top_3_full)

            final = [x[0] for x in top_3[:3]]

            starter = " Did you mean:"

            if len(final) > 0:
                match (len(final)):
                    case 1:
                        help_str = f"{starter} {final[0]}?"
                    case 2:
                        help_str = f"{starter} {final[0]} or {final[1]}?"
                    case _:
                        help_str = f"{starter} {", ".join(final[:-1])}, or {final[-1]}"
            else:
                help_str = "Check your spelling!", False

            return f"Your entry {raw_query.title()} did not match with anything.{help_str}", False

        elif best_match_substring is None:
            return best_match_full[0], True
        else:
            return best_match_substring[0], True

    async def parse(self, to_parse: str = "", headers: dict[str, str] | None = None) -> dict[str, Any] | list[Any] | str:
        try:
            craft_this: client = self.bot.craft_this

            async with craft_this.session.get(to_parse, headers=headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return f"{resp.status} {resp.reason}"
        except Exception as exc:
            return f"400 {exc}"
    
    @staticmethod
    def chunk_text(original: str, max_length: int | None = 2000) -> list[str]:
        max_length = cast(int, max_length)
        # Initial chunking
        chunks = []
        split_text = original.splitlines()
        current_chunk = []

        for split in split_text:
            if len("\n".join(current_chunk) + f"\n{split}") <= max_length:
                current_chunk.append(split)
                continue
            
            chunks.append(current_chunk)
            current_chunk = [split]

        if len(current_chunk) > 0:
            chunks.append(current_chunk)

        # Filtering
        for i, chunk in enumerate(chunks):
            if i == 0:
                continue

            joined = "\n".join(chunk)
            split = joined.strip()

            while joined != split:
                chunk.insert(0, chunks[i-1].pop(-1))

                while len("\n".join(chunk)) > max_length:
                    if i+1 == len(chunks):
                        chunks.append([])
                    chunks[i+1].insert(0, chunk.pop())

                joined = "\n".join(chunk)
                split = joined.strip()

        return chunks
    
    @classmethod
    async def send(cls, result_text: str, reference: commands.Context[objects.Bot] | discord.Message) -> None:

        if isinstance(reference, discord.Message):
            message: discord.Message = reference
        else:
            message = cast(commands.Context[objects.Bot], reference).message

        all_messages = []

        for chunk in cls.chunk_text(result_text):
            ref_msg = message if len(all_messages) == 0 else all_messages[-1]
            
            if (joined := "\n".join(chunk)) != "":
                new_msg = await ref_msg.reply(joined)
                all_messages.append(new_msg)
                await do.sleep_async(0.5)

        await message.edit(content=f"Your command has been processed. See all results:\n{"\n".join([msg.jump_url for msg in all_messages])}", allowed_mentions=discord.AllowedMentions.all())
           
class Cog(commands.Cog, name=name, description="Commands related to Helldivers 2"):
    def __init__(self, bot: objects.Bot):
        self.latest_keywords = ["current", "latest", "now"]

        self.bot = bot
        
        self.convert = Converter()
        self.util = Utilities(self.bot)

        self.cache = Cache()
        self.endpoints: HD2.Endpoints = HD2.Endpoints()

        self.last_liberation_invoke: float | int = -1

        self.DUMP_PATH = os.path.join(self.bot.DIRS.JSON, "hd2_dumps/")

        self.war_info_initialized = asyncio.Event()
        self.ready_900 = asyncio.Event()
        self.ready_300 = asyncio.Event()
        self.ready_60 = asyncio.Event()

        self.get_latest_900s.start()
        self.get_latest_300s.start()
        self.get_latest_60s.start()
        self.get_latest_10s.start()

    async def cog_load(self) -> None:
        def __war_info_initialized(task: asyncio.Task) -> None:
            if type(res := task.result()) == dict:
                self.cache.WarInfo = HD2.Schemas.WarInfo(res)
                self.war_info_initialized.set()
            else:
                asyncio.create_task(self.bot.owner.send("Something went wrong with initializing Helldivers 2."))

        def __war_season_received(task: asyncio.Task) -> None:
            war_id = None
            if type(res := task.result()) == dict:
                war_id = res.get("id")

            self.cache.CurrentWarID = war_id
            self.endpoints.set_season_endpoints(war_id)

            get_war_info_task = asyncio.create_task(self.util.parse(self.endpoints.WarInfo))
            get_war_info_task.add_done_callback(__war_info_initialized)

        get_war_season_task = asyncio.create_task(self.util.parse(self.endpoints.CurrentWarID))
        get_war_season_task.add_done_callback(__war_season_received)
          
    async def cog_unload(self) -> None:
        self.get_latest_900s.cancel()
        self.get_latest_300s.cancel()
        self.get_latest_60s.cancel()
        self.get_latest_10s.cancel()

    async def cog_check(self, ctx) -> bool:
        return self.cache.ready
    
    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CheckFailure):
            setattr(ctx, "error_handled", True)
            await ctx.reply("# Helldivers 2 is not ready!\nThe bot either just started or it has restarted the Helldivers 2 feature-set for updates. As a result, the commands are not yet available for usage. This shouldn't take long - please wait about a minute. If the bot continues to error, please notify @issu immediately.")

    @tasks.loop(seconds=900)
    async def get_latest_900s(self):        
        payloads = {
            "GameClientConfiguration": await self.util.parse(self.endpoints.GameClientConfiguration)
        }

        next_iter = self.get_latest_900s.next_iteration.timestamp() if self.get_latest_900s.next_iteration else None

        for val, data in payloads.items():
            if type(data) == str:
                raise ValueError(f"Invalid data type for payload (str): {data}")

            with open(os.path.join(self.DUMP_PATH, f"{val}.json"), mode="w") as f:
                json.dump(data, f)
        
            setattr(self.cache, val, getattr(HD2.Schemas, val)(data))

        self.bot.timer_cache("helldivers.get_latest_900s", "set", next_iter)

        if not self.ready_900.is_set():
            self.ready_900.set()

    @tasks.loop(seconds=300)
    async def get_latest_300s(self):
        payloads = {
            "MajorOrders": await self.util.parse(self.endpoints.MajorOrders),
            "WarTime": {"WarTime": await self.util.parse(self.endpoints.WarTime), "TimeSinceStart": await self.util.parse(self.endpoints.TimeSinceStart)},
            "Leaderboard": await self.util.parse(self.endpoints.Leaderboard.get("main", ""))
        }

        for val, data in payloads.items():
            if type(data) == str:
                raise ValueError(f"Invalid data type for payload (str): {data}")

            with open(os.path.join(self.DUMP_PATH, f"{val}.json"), mode="w") as f:
                json.dump(data, f)
        
            setattr(self.cache, val, getattr(HD2.Schemas, val)(data))

        next_iter = self.get_latest_300s.next_iteration.timestamp() if self.get_latest_300s.next_iteration else None

        self.bot.timer_cache("helldivers.get_latest_300s", "set", next_iter)

        if not self.ready_300.is_set():
            self.ready_300.set()

    @tasks.loop(seconds=60)
    async def get_latest_60s(self):
        payloads = {
            "NewsFeed": await self.util.parse(self.endpoints.NewsFeed)
        }

        for val, data in payloads.items():
            if type(data) == str:
                raise ValueError(f"Invalid data type for payload (str): {data}")

            with open(os.path.join(self.DUMP_PATH, f"{val}.json"), mode="w") as f:
                json.dump(data, f)

            setattr(self.cache, val, getattr(HD2.Schemas, val)(data))

        war_id = None
        if type(res := await self.util.parse(self.endpoints.CurrentWarID)) == dict:
            war_id = res.get("id")

        old_id = self.cache.CurrentWarID

        if old_id != war_id:
            self.cache.CurrentWarID = war_id
            self.endpoints.set_season_endpoints(war_id)

        next_iter = self.get_latest_60s.next_iteration.timestamp() if self.get_latest_60s.next_iteration else None

        self.bot.timer_cache("helldivers.get_latest_60s", "set", next_iter)

        current_invoke = utils.utcnow().timestamp()
        last_invoke = self.last_liberation_invoke
        self.last_liberation_invoke = utils.utcnow().timestamp()

        if last_invoke != -1 and current_invoke > (last_invoke + 300):
            self.cache.recalculate_lib_estimate(current_invoke - last_invoke)

        if not self.ready_60.is_set():
            self.ready_60.set()

    @tasks.loop(seconds=10)
    async def get_latest_10s(self):
        payloads = {
            "WarStats": await self.util.parse(self.endpoints.WarStats),
            "WarStatus": await self.util.parse(self.endpoints.WarStatus)
        }

        for val, data in payloads.items():
            if type(data) == str:
                raise ValueError(f"Invalid data type for payload (str): {data}")

            with open(os.path.join(self.DUMP_PATH, f"{val}.json"), mode="w") as f:
                json.dump(data, f)

            setattr(self.cache, val, getattr(HD2.Schemas, val)(data))

        next_iter = self.get_latest_10s.next_iteration.timestamp() if self.get_latest_10s.next_iteration else None

        self.bot.timer_cache("helldivers.get_latest_10s", "set", next_iter)

        if self.ready_900.is_set() and self.ready_300.is_set() and self.ready_60.is_set():
            self.cache.remap()
        
    @get_latest_900s.before_loop
    async def before_loop_900s(self):
        await self.before_loop("900s")

        payloads = ["GameClientConfiguration"]

        if (
            (next_invoke := self.bot.timer_cache("helldivers.get_latest_900s")) is not None 
            and (duration := (next_invoke - utils.utcnow().timestamp())) > 0
            ):
            for payload in payloads:
                with open(os.path.join(self.DUMP_PATH, f"{payload}.json"), mode="r") as f:
                    setattr(self.cache, payload, getattr(HD2.Schemas, payload)(json.load(f)))

            self.ready_900.set()

            await do.sleep_async(duration)

    @get_latest_300s.before_loop
    async def before_loop_300s(self):
        await self.before_loop("300s")

        payloads = ["MajorOrders", "WarTime", "Leaderboard"]

        if (
            (next_invoke := self.bot.timer_cache("helldivers.get_latest_300s")) is not None 
            and (duration := (next_invoke - utils.utcnow().timestamp())) > 0
            ):
            for payload in payloads:
                with open(os.path.join(self.DUMP_PATH, f"{payload}.json"), mode="r") as f:
                    setattr(self.cache, payload, getattr(HD2.Schemas, payload)(json.load(f)))

                self.ready_300.set()

            await do.sleep_async(duration)

    @get_latest_60s.before_loop
    async def before_loop_60s(self):
        await self.before_loop("60s")

        payloads = ["NewsFeed"]

        if (
            (next_invoke := self.bot.timer_cache("helldivers.get_latest_60s")) is not None 
            and (duration := (next_invoke - utils.utcnow().timestamp())) > 0
            ):
            self.ready_60.set()

            for payload in payloads:
                with open(os.path.join(self.DUMP_PATH, f"{payload}.json"), mode="r") as f:
                    setattr(self.cache, payload, getattr(HD2.Schemas, payload)(json.load(f)))

            await do.sleep_async(duration)

    @get_latest_10s.before_loop
    async def before_loop_10s(self):
        await self.before_loop("10s")

        payloads = ["WarStats", "WarStatus"]

        if (
            (next_invoke := self.bot.timer_cache("helldivers.get_latest_10s")) is not None 
            and (duration := (next_invoke - utils.utcnow().timestamp())) > 0
            ):
            for payload in payloads:
                with open(os.path.join(self.DUMP_PATH, f"{payload}.json"), mode="r") as f:
                    setattr(self.cache, payload, getattr(HD2.Schemas, payload)(json.load(f)))

            await do.sleep_async(duration)
        
    @get_latest_900s.error
    async def loop_error_900s(self, exc: BaseException):
        await self.loop_error("900s", exc)

    @get_latest_300s.error
    async def loop_error_300s(self, exc: BaseException):
        await self.loop_error("300s", exc)

    @get_latest_60s.error
    async def loop_error_60s(self, exc: BaseException):
        await self.loop_error("60s", exc)

    @get_latest_10s.error
    async def loop_error_10s(self, exc: BaseException):
        await self.loop_error("10s", exc)

    async def before_loop(self, loop: str):
        await self.bot.wait_until_ready()
        await self.war_info_initialized.wait()

    async def loop_error(self, loop: str, exception: BaseException):
        await self.bot.base_error_handler(f"helldivers2.loop.{loop}", exception)

    @commands.group(aliases=["hd", "hd2", "helldivers"], invoke_without_command=True)
    async def helldivers2(self, ctx):
        if ctx.author.id == 526661153250869249:
            return await ctx.reply("\n".join([
                "This for u noah",
                "https://open.spotify.com/track/66TRwr5uJwPt15mfFkzhbi",
                "https://www.youtube.com/watch?v=8UFIYGkROII"
            ]))
        
        await ctx.invoke(command=self.bot.get_command("hd2 status"))

    @helldivers2.command(aliases=["planets"])
    async def planet(self, ctx, *, entry: str | None = None):
        if entry is None:
            return await ctx.reply("# Are you sure about that?\n> `!!` **You are attempting to query all planets** `!!`\n\nThe results will be quite long! If you are sure, use the \"force\" parameter on the next invocation.")
        
        entry = cast(str, entry)

        force_load = (entry := entry.lower()) == "force"
        
        message = await ctx.reply(f"Getting {"all planets..." if force_load else f"info on planet {" ".join([s.capitalize() for s in str(entry).split()])}"}...", mention_author=False)

        if force_load:
            title = "# 🌐 All Planets"

            all_texts = []

            planets_by_sector_by_faction = cast(dict[str, dict[int, list[str]]], dict.fromkeys([s.name for s in self.cache.WarInfo.sectors]))

            for planet in self.cache.WarInfo.planets:
                sector_dict = planets_by_sector_by_faction.get(planet.sector.name) or {}
                faction_list = sector_dict.get(int(planet.status.current_faction.id)) or []

                faction_list.append(planet.name)
                sector_dict[int(planet.status.current_faction.id)] = faction_list
                planets_by_sector_by_faction[planet.sector.name] = sector_dict
                
            planets_by_sector_by_faction = dict(sorted(planets_by_sector_by_faction.items()))

            for init_sector, init_factions in planets_by_sector_by_faction.items():
                planets_by_sector_by_faction[init_sector] = dict(sorted(init_factions.items()))

                for init_faction, init_planets in planets_by_sector_by_faction[init_sector].items():
                    planets_by_sector_by_faction[init_sector][init_faction] = sorted(init_planets)
                
            for sorted_sector, sorted_factions in planets_by_sector_by_faction.items():
                all_texts.append(f"- {self.convert.label(sorted_sector)}" if sorted_sector != "Sol" else "- Sol System")

                for sorted_faction, sorted_planets in sorted_factions.items():
                    planet_text = "None!" if len(sorted_planets) == 0 else sorted_planets[0] if len(sorted_planets) == 1 else f"{sorted_planets[0]} and {sorted_planets[1]}" if len(sorted_planets) == 2 else f"{", ".join([p for p in sorted_planets][:-1])}, and {sorted_planets[-1]}"
                    all_texts.append(f" - {next(f.emoji for f in self.cache.WarInfo.factions if f.id == sorted_faction)} {planet_text}")

            parsed_message = f"{title}\n{"\n".join(all_texts)}"
        else:
            parsed_entry, success = self.util.auto_complete(entry, [planet.name for planet in self.cache.WarInfo.planets])
                    
            if not success:
                return await self.util.send(f"# The planet \"{" ".join([s.capitalize() for s in entry.split()])}\" could not be found! Check your spelling!", message)

            try:
                planet = next((planet for planet in self.cache.WarInfo.planets if planet.name == parsed_entry))
            except:
                return await self.util.send("An error occurred while trying to get planet info.", message)
            
            current_owner = planet.status.current_faction
            initial_owner = planet.initial_faction

            reg_faction_text = f"{current_owner.emoji} Under {current_owner.name} Control)"
            faction_text = f"{planet.home_world_of.emoji} {planet.home_world_of.name} Homeworld ({reg_faction_text})" if planet.home_world_of else f"{reg_faction_text} [{initial_owner.emoji} Initially {initial_owner.name}]"

            is_liberated = planet.status.current_faction.id == 1

            if is_liberated:
                symbol = "="
                progress_text = None
            elif planet.status.net_rate > 0.0005:
                symbol = ">"
                progress_text = "⬆️ [PROGRESSING]"
            elif planet.status.net_rate > -0.0005:
                symbol = "|"
                progress_text = "⏸️ [STALEMATE]"
            else:
                symbol = "<"
                progress_text = "⬇️ [REGRESSING]"

            progress_bar_value = int(planet.status.liberation * 40)
            progress_bar = f"`|{"="*(progress_bar_value-1)}{symbol}{" "*(40-progress_bar_value)}|`"

            lines = list(filter(None, [
                f"# <:helldivers2:1218539103436669008> {planet.name} ({self.convert.label(planet.sector.name)})",
                f"## {faction_text}",
                f"\n> 🌐  **Planet Details**",
                f"- **Relative Position:** `({planet.position.x}, {planet.position.y})`",
                f"- **Helldivers Active:** `{planet.status.players}` Helldivers",
                f"- **Is Playable:** {planet.playable}",
                f"\n> <:hellpod:1218539133853765763> **Liberation Status**",
                f"- `{(planet.status.liberation*100):.6f}%` **Liberated** ({planet.status.current_health}/{planet.max_health} HP)",
                f" - {progress_bar}",
                f" - {progress_text}" if progress_text else None,
                f" - **Liberation** {self.convert.to_discord(planet.status.estimated_liberation_time) if planet.status.estimated_liberation_time else "`Unfeasable right now`"}" if not is_liberated else None,
                f" - **Liberation Rate:** `~{(planet.status.rate or 0):.6f}%/hr` ({planet.status.raw_rate or 0} HP/hr)" if not is_liberated else None,
                f" - **Planet Regen Rate:** `-{(planet.status.regen_per_hour*100):.6f}%/hr`" if not is_liberated else None,
                f" - **Net Liberation Rate:** `~{(planet.status.net_rate*100):.6f}%/hr`" if not is_liberated else None,
                f"\n> 🏹 **Attacks**",
                f"- __Attacking__\n - {"\n - ".join([f"{atk.target.status.current_faction.emoji} {atk.target.name}" for atk in planet.conflicts.get("to", [])]) if len(planet.conflicts.get("to", [])) > 0 else "None!"}",
                f"- __Attacked By__\n - {"\n - ".join([f"{_def.target.status.current_faction.emoji} {_def.source.name}" for _def in planet.conflicts.get("from", [])]) if len(planet.conflicts.get("from", [])) > 0 else "None!"}",
                f"\n> 🗺  **Campaigns Involved**\n- {"\n- ".join([f"Campaign `#{campaign.id}`: {campaign.type.get(is_liberated) if type(campaign.type) == dict else campaign.type}" for campaign in planet.involved_campaigns]) if len(planet.involved_campaigns) > 0 else "None!"}"
            ]))

            parsed_message = "\n".join(lines)

        return await self.util.send(parsed_message, message)

    @helldivers2.command(aliases=["campaigns"])
    async def campaign(self, ctx):
        message = await ctx.reply(f"Getting all campaigns...", mention_author=False)
    
        title = f"# All Campaigns"
        text = "\n".join([f"- {self.convert.label(campaign.type.get(campaign.planet.status.current_faction.id == 1, "Unknown") if type(campaign.type) == dict else str(campaign.type), "Campaign")} on {campaign.planet.status.current_faction.emoji} {campaign.planet.name}" for campaign in self.cache.WarStatus.campaigns])

        parsed_message = f"{title}\n{text}"
        return await self.util.send(parsed_message, message)
    
    @helldivers2.command(aliases=["events"])
    async def event(self, ctx, *, entry: str | None = None):
        await ctx.reply("Coming soon!")

    @helldivers2.command(aliases=["effects"])
    async def effect(self, ctx, *, entry: str | None = None):
        await ctx.reply("Coming soon!")

    @helldivers2.command(aliases=["statuses"])
    async def status(self, ctx, *, entry: str | None = None):
        await ctx.reply("Hi")

async def setup(bot):
    await bot.add_cog(Cog(bot), override=True)

async def teardown(bot):
    await bot.remove_cog(name)
