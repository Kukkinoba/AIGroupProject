% Group Project: Road Network Path finding 
% Group Members: Elisha Beverly (2100145), Rande Wright (2008316), Keston Cole (2210260), Chamarie Taylor (2100027), Antonio Goldson (2206840)
% Prolog part of the project

:- dynamic road/6.   % road(Source, Dest, DistanceKm, Type, TimeMin, Status)
                     % Type   = paved | unpaved | broken_cisterns | deep_potholes
                     % Status  = open | closed

% ============================================================
% Rural Roads Network for Clarendon

% ---------------------------
% May Pen Area
road(may_pen, denbigh, 4, paved, 6, open).
road(denbigh, may_pen, 4, paved, 6, open).
road(denbigh, osbourne_store, 5, paved, 8, open).
road(osbourne_store, denbigh, 5, paved, 8, open).
road(osbourne_store, race_course, 6, paved, 10, open).
road(race_course, osbourne_store, 6, paved, 10, open).
road(may_pen, four_paths, 7, paved, 12, open).
road(four_paths, may_pen, 7, paved, 12, open).
road(four_paths, new_longsville, 8, unpaved, 18, open).
road(new_longsville, four_paths, 8, unpaved, 18, open).
road(new_longsville, longsville_park, 4, unpaved, 10, open).
road(longsville_park, new_longsville, 4, unpaved, 10, open).

% ---------------------------
% Hayes / South Coast
road(may_pen, hayes, 14, paved, 18, open).
road(hayes, may_pen, 14, paved, 18, open).
road(hayes, four_paths, 8, paved, 12, open).
road(four_paths, hayes, 8, paved, 12, open).
road(hayes, rock, 6, paved, 8, open).
road(rock, hayes, 6, paved, 8, open).
road(rock, milk_river, 5, paved, 7, open).
road(milk_river, rock, 5, paved, 7, open).
road(milk_river, sandy_bay, 9, paved, 14, open).
road(sandy_bay, milk_river, 9, paved, 14, open).

% ---------------------------
% Chapelton / Summerfield
road(may_pen, chapelton, 18, paved, 25, open).
road(chapelton, may_pen, 18, paved, 25, open).
road(chapelton, summerfield, 4, paved, 6, open).
road(summerfield, chapelton, 4, paved, 6, open).
road(summerfield, kensington, 6, unpaved, 14, open).
road(kensington, summerfield, 6, unpaved, 14, open).
road(kensington, race_course, 9, unpaved, 20, open).
road(race_course, kensington, 9, unpaved, 20, open).

% ---------------------------
% Freetown / Lionel Town
road(four_paths, freetown, 6, paved, 9, open).
road(freetown, four_paths, 6, paved, 9, open).
road(freetown, sandy_bay, 10, paved, 15, open).
road(sandy_bay, freetown, 10, paved, 15, open).
road(freetown, lionel_town, 4, paved, 7, open).
road(lionel_town, freetown, 4, paved, 7, open).
road(lionel_town, race_course, 8, paved, 12, open).
road(race_course, lionel_town, 8, paved, 12, open).

% ---------------------------
% Rough Roads
road(summerfield, new_longsville, 12, broken_cisterns, 30, open).
road(new_longsville, summerfield, 12, broken_cisterns, 30, open).
road(new_longsville, chapelton, 10, deep_potholes, 35, open).
road(chapelton, new_longsville, 10, deep_potholes, 35, open).

% ---------------------------
% Seasonal / Closed Roads
road(osbourne_store, longsville_park, 7, unpaved, 20, closed).
road(longsville_park, osbourne_store, 7, unpaved, 20, closed).
road(kensington, four_paths, 11, broken_cisterns, 28, closed).
road(four_paths, kensington, 11, broken_cisterns, 28, closed).


% ============================================================
% Allowed Edges 

allowed(Type, Status, Criteria) :-
    Status = open,
    \+ (member(avoid_unpaved, Criteria),       Type = unpaved),
    \+ (member(avoid_broken, Criteria),        Type = broken_cisterns),
    \+ (member(avoid_deep_potholes, Criteria), Type = deep_potholes).

edge(Crit, From, To, Dist, Time, Type) :-
    road(From, To, Dist, Type, Time, Status),
    allowed(Type, Status, Crit).


% ============================================================
% Breadth First Search - BFS

bfs(Crit, Start, Goal, Path, Dist, Time) :-
    bfs_queue(Crit, [[Start]], Goal, RevPath),
    reverse(RevPath, Path),
    path_cost(Crit, Path, Dist, Time).

bfs_queue(_, [[Goal | Rest] | _], Goal, [Goal | Rest]).
bfs_queue(Crit, [[Current | Rest] | Q], Goal, P2) :-
    findall([Next, Current | Rest],
            ( edge(Crit, Current, Next, _, _, _),
              \+ member(Next, [Current | Rest]) ),
            Children),
    append(Q, Children, Q2),
    bfs_queue(Crit, Q2, Goal, P2).


% ============================================================
% Dijkstra

dijkstra(Mode, Crit, Start, Goal, Path, Dist, Time) :-
    dijkstra_queue(Mode, Crit, [state(0, 0, [Start])], Goal, RevPath, Dist, Time),
    reverse(RevPath, Path).

dijkstra_queue(_, _, [state(D, T, [Goal | R]) | _], Goal, [Goal | R], D, T).

dijkstra_queue(Mode, Crit, [state(D0, T0, [Curr | R]) | Others],
               Goal, Path, Dist, Time) :-
    findall(state(D1, T1, [Next, Curr | R]),
            ( edge(Crit, Curr, Next, StepD, StepT, _),
              \+ member(Next, [Curr | R]),
              D1 is D0 + StepD,
              T1 is T0 + StepT ),
            Children),
    insert_children(Mode, Children, Others, NewQ),
    dijkstra_queue(Mode, Crit, NewQ, Goal, Path, Dist, Time).

insert_children(_, [], Q, Q).
insert_children(M, [S|R], Q, Out) :-
    insert_state(M, S, Q, Q1),
    insert_children(M, R, Q1, Out).

insert_state(_, S, [], [S]).
insert_state(M, S, [Q|Rest], [S, Q | Rest]) :-
    better(M, S, Q), !.
insert_state(M, S, [Q|Rest], [Q|Rest2]) :-
    insert_state(M, S, Rest, Rest2).

better(distance, state(D1,_,_), state(D2,_,_)) :- D1 < D2.
better(time,     state(_,T1,_), state(_,T2,_)) :- T1 < T2.
better(_,        state(D1,_,_), state(D2,_,_)) :- D1 < D2.


% ============================================================
% A* Search

a_star(Mode, Crit, Start, Goal, Path, Dist, Time) :-
    a_star_queue(Mode, Crit, Goal, [state(0, 0, 0, [Start])],
                 Goal, Rev, Dist, Time),
    reverse(Rev, Path).

a_star_queue(_, _, _, [state(_,D,T,[Goal|R])|_],
             Goal, [Goal|R], D, T).

a_star_queue(M, Crit, Goal, [state(_,GD,GT,[Curr|R])|Others],
             Goal, Path, Dist, Time) :-

    findall(state(F1, D1, T1, [Next, Curr|R]),
            ( edge(Crit, Curr, Next, StepD, StepT, _),
              \+ member(Next, [Curr|R]),
              D1 is GD + StepD,
              T1 is GT + StepT,
              heuristic(M, Next, Goal, H),
              score(M, D1, T1, H, F1) ),
            Children),

    insert_children_astar(M, Children, Others, NewQ),
    a_star_queue(M, Crit, Goal, NewQ, Goal, Path, Dist, Time).

heuristic(_,_,_,0).  % placeholder heuristic

score(distance,D,_,H,F) :- F is D + H.
score(time,    _,T,H,F) :- F is T + H.
score(_,       D,_,H,F) :- F is D + H.

insert_children_astar(_,[],Q,Q).
insert_children_astar(M,[S|R],Q2,Out) :-
    insert_state_astar(M,S,Q2,Q3),
    insert_children_astar(M,R,Q3,Out).

insert_state_astar(_,S,[],[S]).
insert_state_astar(M,S,[Q|Rest],[S,Q|Rest]) :-
    better_astar(M,S,Q), !.
insert_state_astar(M,S,[Q|Rest],[Q|Rest2]) :-
    insert_state_astar(M,S,Rest,Rest2).

better_astar(_, state(F1,_,_,_), state(F2,_,_,_)) :- F1 < F2.


% ============================================================
% Path Cost Calculation
path_cost(_, [_], 0, 0).
path_cost(Crit, [A, B | Rest], Dist, Time) :-
    edge(Crit, A, B, D1, T1, _),
    path_cost(Crit, [B | Rest], D2, T2),
    Dist is D1 + D2,
    Time is T1 + T2.


% ============================================================
% Criteria

criteria_list(shortest_distance,   []).
criteria_list(fastest_time,       []).
criteria_list(avoid_unpaved,      [avoid_unpaved]).
criteria_list(avoid_broken,       [avoid_broken]).
criteria_list(avoid_deep_potholes,[avoid_deep_potholes]).
criteria_list(loose_constraints,  []).

mode_for(shortest_distance,   distance, dijkstra).
mode_for(fastest_time,       time,     dijkstra).
mode_for(avoid_unpaved,      distance, dijkstra).
mode_for(avoid_broken,       distance, dijkstra).
mode_for(avoid_deep_potholes,distance, dijkstra).
mode_for(loose_constraints,  distance, bfs).

% ============================================================
% Export edges for Python
export_edges :-
    road(A, B, D, Type, Time, Status),
    format("E~w,~w,~w,~w,~w,~w~n",
           [A, B, D, Type, Time, Status]),
    fail.
export_edges.


% ============================================================
% Main Interface

run_query(CritAtom, Start, Goal) :-
    criteria_list(CritAtom, CritList),
    mode_for(CritAtom, Mode, Algo),
    ( Algo = bfs ->
        bfs(CritList, Start, Goal, Path, D, T)
    ; Algo = dijkstra ->
        dijkstra(Mode, CritList, Start, Goal, Path, D, T)
    ; Algo = astar ->
        a_star(Mode, CritList, Start, Goal, Path, D, T)
    ),
    format('~w|~2f|~2f', [Path, D, T]).