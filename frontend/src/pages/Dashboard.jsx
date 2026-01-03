import React from 'react'
import { API_BASE_URL } from '../config/api'
import { useQuery } from '@tanstack/react-query'
import { Calendar, Users, TrendingUp, AlertCircle, MapPin, Clock } from 'lucide-react'

const Dashboard = () => {
  // Fetch upcoming fixtures
  const { data: fixturesData, isLoading: fixturesLoading } = useQuery({
    queryKey: ['upcoming-fixtures'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/fixtures/upcoming?limit=1`)
      return res.json()
    }
  })

  // Fetch opponents list
  const { data: opponentsData } = useQuery({
    queryKey: ['opponents'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/opponents`)
      return res.json()
    }
  })

  const nextMatch = fixturesData?.fixtures?.[0]
  const homeTeam = nextMatch?.teams?.home
  const awayTeam = nextMatch?.teams?.away
  const isGilHome = homeTeam?.id === 228
  const opponent = isGilHome ? awayTeam : homeTeam
  const matchDate = nextMatch?.fixture?.date ? new Date(nextMatch.fixture.date) : null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-gray-600 mt-2">Gil Vicente FC Tactical Intelligence Platform</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="tactical-card bg-gradient-to-br from-blue-50 to-blue-100 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-700 font-medium">Season</p>
              <p className="text-3xl font-bold text-blue-900">2025</p>
            </div>
            <Calendar className="text-blue-500" size={40} />
          </div>
        </div>

        <div className="tactical-card bg-gradient-to-br from-green-50 to-green-100 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-700 font-medium">Opponents Tracked</p>
              <p className="text-3xl font-bold text-green-900">{opponentsData?.count || 0}</p>
            </div>
            <Users className="text-green-500" size={40} />
          </div>
        </div>

        <div className="tactical-card bg-gradient-to-br from-purple-50 to-purple-100 border-l-4 border-purple-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-700 font-medium">League</p>
              <p className="text-xl font-bold text-purple-900">Primeira Liga</p>
            </div>
            <TrendingUp className="text-purple-500" size={40} />
          </div>
        </div>

        <div className="tactical-card bg-gradient-to-br from-red-50 to-red-100 border-l-4 border-red-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-red-700 font-medium">Team ID</p>
              <p className="text-3xl font-bold text-red-900">228</p>
            </div>
            <AlertCircle className="text-red-500" size={40} />
          </div>
        </div>
      </div>

      {/* Next Match Preview */}
      <div className="tactical-card bg-gradient-to-r from-blue-600 to-blue-800 text-white">
        <h3 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <Calendar size={28} />
          Next Match
        </h3>
        
        {fixturesLoading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
            <p className="mt-4">Loading match data...</p>
          </div>
        ) : nextMatch ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-6 bg-white/10 backdrop-blur rounded-lg">
              <div className="text-center flex-1">
                <p className="text-2xl font-bold">{homeTeam?.name}</p>
                <span className="inline-block mt-2 px-3 py-1 bg-white/20 rounded-full text-sm">
                  {isGilHome ? '🏠 Home' : '✈️ Away'}
                </span>
              </div>
              <div className="text-center px-8">
                <p className="text-4xl font-bold mb-2">VS</p>
                {matchDate && (
                  <>
                    <p className="text-lg font-semibold">
                      {matchDate.toLocaleDateString('pt-PT', { 
                        day: '2-digit', 
                        month: 'short', 
                        year: 'numeric' 
                      })}
                    </p>
                    <p className="text-sm opacity-90 flex items-center gap-1 justify-center mt-1">
                      <Clock size={16} />
                      {matchDate.toLocaleTimeString('pt-PT', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </p>
                  </>
                )}
              </div>
              <div className="text-center flex-1">
                <p className="text-2xl font-bold">{awayTeam?.name}</p>
                <span className="inline-block mt-2 px-3 py-1 bg-white/20 rounded-full text-sm">
                  {!isGilHome ? '🏠 Home' : '✈️ Away'}
                </span>
              </div>
            </div>
            
            <div className="flex items-center gap-2 text-sm opacity-90">
              <MapPin size={16} />
              <span>{nextMatch.fixture.venue?.name}</span>
            </div>

            <div className="pt-4 border-t border-white/20">
              <p className="text-sm opacity-90 mb-2">Quick Analysis:</p>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-white/10 p-3 rounded">
                  <p className="font-semibold">Opponent: {opponent?.name}</p>
                </div>
                <div className="bg-white/10 p-3 rounded">
                  <p className="font-semibold">Competition: {nextMatch.league.name}</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-center py-8">No upcoming matches found</p>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="tactical-card hover:shadow-lg transition-shadow cursor-pointer bg-blue-50 border-l-4 border-blue-500">
          <div className="flex items-center gap-4">
            <Calendar className="text-blue-600" size={32} />
            <div>
              <h4 className="font-bold text-lg">View All Fixtures</h4>
              <p className="text-sm text-gray-600">See the complete match schedule</p>
            </div>
          </div>
        </div>

        <div className="tactical-card hover:shadow-lg transition-shadow cursor-pointer bg-green-50 border-l-4 border-green-500">
          <div className="flex items-center gap-4">
            <Users className="text-green-600" size={32} />
            <div>
              <h4 className="font-bold text-lg">Analyze Opponents</h4>
              <p className="text-sm text-gray-600">Tactical profiles and insights</p>
            </div>
          </div>
        </div>

        <div className="tactical-card hover:shadow-lg transition-shadow cursor-pointer bg-purple-50 border-l-4 border-purple-500">
          <div className="flex items-center gap-4">
            <TrendingUp className="text-purple-600" size={32} />
            <div>
              <h4 className="font-bold text-lg">Tactical Reports</h4>
              <p className="text-sm text-gray-600">Deep dive analysis and recommendations</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
